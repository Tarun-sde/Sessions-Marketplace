from django.contrib.auth.models import AbstractUser
from django.db import models


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
