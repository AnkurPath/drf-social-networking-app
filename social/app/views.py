from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from .models import CustomUser, FriendRequest
from .serializers import (
    UserSignupSerializer, UserLoginSerializer, UserSearchSerializer, FriendRequestSerializer
)
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import timedelta

class UserSignupView(generics.CreateAPIView):
    serializer_class = UserSignupSerializer
    permission_classes = [permissions.AllowAny]

class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()
        password = serializer.validated_data['password']
        user = authenticate(email=email, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        else:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class UserSearchView(generics.ListAPIView):
    serializer_class = UserSearchSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = CustomUser.objects.all()
        keyword = self.request.query_params.get('keyword', None)
        if keyword:
            queryset = queryset.filter(
                Q(email__iexact=keyword) | Q(first_name__icontains=keyword) | Q(last_name__icontains=keyword)
            )
        return queryset

class FriendRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        to_user_id = request.data.get('to_user')
        if not to_user_id:
            return Response({'detail': 'to_user is required'}, status=status.HTTP_400_BAD_REQUEST)
        to_user = CustomUser.objects.get(id=to_user_id)

        # Rate limit: no more than 3 requests per minute
        one_minute_ago = timezone.now() - timedelta(minutes=1)
        recent_requests = FriendRequest.objects.filter(
            from_user=request.user, timestamp__gte=one_minute_ago
        ).count()
        if recent_requests >= 3:
            return Response({'detail': 'Rate limit exceeded: No more than 3 requests per minute'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)

        friend_request, created = FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user)
        if not created:
            return Response({'detail': 'Friend request already sent'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(FriendRequestSerializer(friend_request).data, status=status.HTTP_201_CREATED)

    def put(self, request, *args, **kwargs):
        request_id = request.data.get('request_id')
        action = request.data.get('action')
        if not request_id or not action:
            return Response({'detail': 'request_id and action are required'}, status=status.HTTP_400_BAD_REQUEST)

        friend_request = FriendRequest.objects.get(id=request_id, to_user=request.user)
        if action == 'accept':
            friend_request.is_accepted = True
            friend_request.save()
            return Response({'detail': 'Friend request accepted'}, status=status.HTTP_200_OK)
        elif action == 'reject':
            friend_request.delete()
            return Response({'detail': 'Friend request rejected'}, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

class FriendListView(generics.ListAPIView):
    serializer_class = UserSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CustomUser.objects.filter(
            Q(sent_requests__to_user=self.request.user, sent_requests__is_accepted=True) |
            Q(received_requests__from_user=self.request.user, received_requests__is_accepted=True)
        ).distinct()

class PendingRequestsView(generics.ListAPIView):
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FriendRequest.objects.filter(to_user=self.request.user, is_accepted=False)
