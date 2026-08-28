import uuid
from django.contrib.auth import get_user_model
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import (
    UserSerializer,
    UserProfileUpdateSerializer,
    GoogleAuthSerializer
)
from .oauth import verify_google_id_token

User = get_user_model()


class HealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "ok", "service": "ahoum-backend"})


class GoogleAuthView(APIView):
    """
    POST /api/auth/google/
    Exchanges a verified Google ID token for JWT access + refresh tokens and user profile.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        id_token_str = serializer.validated_data['id_token']
        claims = verify_google_id_token(id_token_str)

        sub = claims['sub']
        email = claims['email']
        name = claims.get('name', '')
        avatar_url = claims.get('picture', '')

        # 1. Lookup by Google stable provider + sub
        user = User.objects.filter(oauth_provider='google', oauth_sub=sub).first()

        if not user:
            # 2. If not found by sub, check if user exists by verified email
            user = User.objects.filter(email__iexact=email).first()
            if user:
                # Link Google OAuth identity to existing email user
                user.oauth_provider = 'google'
                user.oauth_sub = sub
                if not user.avatar_url and avatar_url:
                    user.avatar_url = avatar_url
                user.save(update_fields=['oauth_provider', 'oauth_sub', 'avatar_url'])
            else:
                # 3. Create new user
                # Ensure unique username
                base_username = email.split('@')[0]
                username = base_username
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{uuid.uuid4().hex[:6]}"

                name_parts = name.split(' ', 1) if name else ['', '']
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ''

                user = User.objects.create(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    oauth_provider='google',
                    oauth_sub=sub,
                    avatar_url=avatar_url,
                    is_creator=False
                )

        # Generate JWT tokens via SimpleJWT
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class CurrentUserProfileView(APIView):
    """
    GET /api/me/ - Fetch current authenticated user's profile.
    PATCH /api/me/ - Update allowed profile fields (name, bio, avatar_url, is_creator).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()
        return Response(UserSerializer(updated_user).data, status=status.HTTP_200_OK)
