from django.urls import path
from .views import (
    UserSignupView, UserLoginView, UserSearchView, FriendRequestView, FriendListView, PendingRequestsView
)

urlpatterns = [
    path('signup/', UserSignupView.as_view(), name='signup'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('search/', UserSearchView.as_view(), name='user_search'),
    path('friend-request/', FriendRequestView.as_view(), name='friend_request'),
    path('friends/', FriendListView.as_view(), name='friend_list'),
    path('pending-requests/', PendingRequestsView.as_view(), name='pending_requests'),
]
