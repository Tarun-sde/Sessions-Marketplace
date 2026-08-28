import uuid
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Session, Booking
from .permissions import IsCreator, IsSessionOwnerOrReadOnly, IsBookingOwner
from .exceptions import ConflictException
from .serializers import (
    UserSerializer,
    UserProfileUpdateSerializer,
    GoogleAuthSerializer,
    SessionSerializer,
    BookingCreateSerializer,
    BookingSerializer,
    UserBookingItemSerializer,
    CreatorBookingItemSerializer
)
from .oauth import verify_google_id_token

User = get_user_model()


class HealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "ok", "service": "ahoum-backend"})


# ==============================================================================
# Authentication & User Profile Views
# ==============================================================================

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
                # 3. Create new user with unique username
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


# ==============================================================================
# Session Management Views
# ==============================================================================

class SessionListCreateView(APIView):
    """
    GET /api/sessions/ - Catalog listing available to all authenticated users.
    POST /api/sessions/ - Creator-only session creation.
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsCreator()]
        return [permissions.IsAuthenticated()]

    def get(self, request):
        sessions = Session.objects.select_related('creator').order_by('starts_at')
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save(creator=request.user)
        return Response(SessionSerializer(session).data, status=status.HTTP_201_CREATED)


class SessionDetailView(APIView):
    """
    GET /api/sessions/<id>/ - View session details (authenticated users).
    PATCH /api/sessions/<id>/ - Update session details (owner only).
    DELETE /api/sessions/<id>/ - Delete session (owner only).
    """
    permission_classes = [IsSessionOwnerOrReadOnly]

    def get_object(self, pk):
        session = get_object_or_404(Session.objects.select_related('creator'), pk=pk)
        self.check_object_permissions(self.request, session)
        return session

    def get(self, request, pk):
        session = self.get_object(pk)
        serializer = SessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        session = self.get_object(pk)
        serializer = SessionSerializer(session, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_session = serializer.save()
        return Response(SessionSerializer(updated_session).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        session = self.get_object(pk)
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionBookingsListView(APIView):
    """
    GET /api/sessions/<id>/bookings/ - Creator booking count/list for own session.
    Only the session creator can view booking list.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        session = get_object_or_404(Session, pk=pk)
        if session.creator_id != request.user.id:
            raise PermissionDenied("You can only view bookings for sessions you created.", code="forbidden")

        bookings = session.bookings.select_related('user').order_by('-created_at')
        serializer = CreatorBookingItemSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==============================================================================
# Concurrency-Safe Booking Views
# ==============================================================================

class BookingCreateView(APIView):
    """
    POST /api/bookings/
    Books a session with PostgreSQL row-level locking (select_for_update) inside an atomic transaction.
    Guarantees that capacity is never oversold under concurrent races.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data['session_id']

        with transaction.atomic():
            # 1. Lock the Session row in PostgreSQL
            try:
                session = Session.objects.select_for_update().get(id=session_id)
            except Session.DoesNotExist:
                raise NotFound("Session not found.", code="session_not_found")

            # 2. Check if session has already started
            if session.starts_at <= timezone.now():
                raise ConflictException(
                    code="SESSION_ALREADY_STARTED",
                    message="This session has already started."
                )

            # 3. Fast application-level double-booking check
            if Booking.objects.filter(user=request.user, session=session, status=Booking.STATUS_ACTIVE).exists():
                raise ConflictException(
                    code="ALREADY_BOOKED",
                    message="You already have an active booking for this session."
                )

            # 4. Fresh count of active bookings under PostgreSQL row lock
            active_count = Booking.objects.filter(session=session, status=Booking.STATUS_ACTIVE).count()
            if active_count >= session.capacity:
                raise ConflictException(
                    code="SESSION_FULL",
                    message="This session has no remaining seats."
                )

            # 5. Insert booking with DB partial unique index backstop
            try:
                booking = Booking.objects.create(
                    user=request.user,
                    session=session,
                    status=Booking.STATUS_ACTIVE
                )
            except IntegrityError:
                raise ConflictException(
                    code="ALREADY_BOOKED",
                    message="You already have an active booking for this session."
                )

            return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class UserBookingsMineView(APIView):
    """
    GET /api/bookings/mine/
    Returns user's own bookings split into active and past, computed at read time from session.starts_at.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        bookings = Booking.objects.filter(user=request.user).select_related('session', 'session__creator').order_by('-created_at')
        now = timezone.now()

        active_bookings = []
        past_bookings = []

        for booking in bookings:
            # Active only if booking is active AND session starts in the future
            if booking.status == Booking.STATUS_ACTIVE and booking.session.starts_at > now:
                active_bookings.append(booking)
            else:
                past_bookings.append(booking)

        return Response({
            "active": UserBookingItemSerializer(active_bookings, many=True).data,
            "past": UserBookingItemSerializer(past_bookings, many=True).data
        }, status=status.HTTP_200_OK)


class BookingCancelView(APIView):
    """
    DELETE /api/bookings/<id>/
    Cancels user's active booking, immediately freeing the seat for other users.
    Locks the Session row to serialize against concurrent booking requests.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        with transaction.atomic():
            try:
                booking = Booking.objects.select_related('session').get(id=pk)
            except Booking.DoesNotExist:
                raise NotFound("Booking not found.", code="booking_not_found")

            if booking.user_id != request.user.id:
                raise PermissionDenied("You do not have permission to cancel this booking.", code="forbidden")

            # Acquire row lock on parent Session to serialize cancellation with concurrent bookings
            Session.objects.select_for_update().get(id=booking.session_id)

            if booking.status != Booking.STATUS_CANCELLED:
                booking.status = Booking.STATUS_CANCELLED
                booking.save(update_fields=['status'])

            return Response({
                "status": "cancelled",
                "message": "Booking cancelled successfully."
            }, status=status.HTTP_200_OK)
