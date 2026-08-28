from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom user model for Ahoum Sessions Marketplace.
    Configured upfront before initial migrations to avoid auth_user migration lock-in.
    """
    email = models.EmailField(unique=True)
    is_creator = models.BooleanField(default=False)
    oauth_provider = models.CharField(max_length=50, blank=True, default='')
    oauth_sub = models.CharField(max_length=255, blank=True, default='')
    bio = models.TextField(blank=True, default='')
    avatar_url = models.URLField(max_length=500, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['oauth_provider', 'oauth_sub'],
                name='unique_oauth_user',
                condition=models.Q(oauth_provider__gt='', oauth_sub__gt='')
            )
        ]

    def __str__(self):
        return self.email or self.username

    @property
    def display_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.first_name or self.username or self.email


class Session(models.Model):
    """
    Session offered by a Creator in the marketplace.
    """
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_sessions'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    starts_at = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    location = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['starts_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(capacity__gte=1),
                name='session_capacity_gte_1'
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.starts_at})"

    @property
    def active_booking_count(self):
        """Live count of active bookings. Never cached."""
        return self.bookings.filter(status=Booking.STATUS_ACTIVE).count()

    @property
    def remaining_seats(self):
        """Display-only derived remaining seats."""
        return max(0, self.capacity - self.active_booking_count)

    @property
    def is_started(self):
        """Display helper indicating if start time has passed."""
        return self.starts_at <= timezone.now()


class Booking(models.Model):
    """
    Booking of a Session by a User.
    Enforces at most ONE active booking per (user, session) pair via partial unique index.
    """
    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'session'],
                condition=models.Q(status='active'),
                name='unique_active_user_session_booking'
            )
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.session.title} [{self.status}]"
