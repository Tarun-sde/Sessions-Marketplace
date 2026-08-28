from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    HealthCheckView,
    GoogleAuthView,
    CurrentUserProfileView
)

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('auth/google/', GoogleAuthView.as_view(), name='google_auth'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', CurrentUserProfileView.as_view(), name='current_user_profile'),
]
