from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    HealthCheckView,
    GoogleAuthView,
    CurrentUserProfileView,
    SessionListCreateView,
    SessionDetailView,
    SessionBookingsListView,
    BookingCreateView,
    UserBookingsMineView,
    BookingCancelView
)

urlpatterns = [
    # Health & System
    path('health/', HealthCheckView.as_view(), name='health_check'),

    # Auth & Profile
    path('auth/google/', GoogleAuthView.as_view(), name='google_auth'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', CurrentUserProfileView.as_view(), name='current_user_profile'),

    # Sessions
    path('sessions/', SessionListCreateView.as_view(), name='session_list_create'),
    path('sessions/<int:pk>/', SessionDetailView.as_view(), name='session_detail'),
    path('sessions/<int:pk>/bookings/', SessionBookingsListView.as_view(), name='session_bookings_list'),

    # Bookings
    path('bookings/', BookingCreateView.as_view(), name='booking_create'),
    path('bookings/mine/', UserBookingsMineView.as_view(), name='user_bookings_mine'),
    path('bookings/<int:pk>/', BookingCancelView.as_view(), name='booking_cancel'),
]
