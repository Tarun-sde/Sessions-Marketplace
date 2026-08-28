from django.utils import timezone
from rest_framework import serializers
from .models import User, Session, Booking


class UserSerializer(serializers.ModelSerializer):
    """
    Public profile representation of a User.
    Excludes sensitive/internal fields (password, oauth_sub, groups, etc.).
    """
    name = serializers.CharField(source='display_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'first_name', 'last_name', 'bio', 'avatar_url', 'is_creator']
        read_only_fields = ['id', 'email', 'name']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for PATCH /api/me/.
    Allows updating only own name, bio, avatar_url, and is_creator flag.
    Strictly forbids modifying id, email, oauth_provider, oauth_sub, password.
    """
    name = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = User
        fields = ['name', 'first_name', 'last_name', 'bio', 'avatar_url', 'is_creator']

    def update(self, instance, validated_data):
        name = validated_data.pop('name', None)
        if name is not None:
            parts = name.strip().split(' ', 1)
            instance.first_name = parts[0]
            instance.last_name = parts[1] if len(parts) > 1 else ''

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class GoogleAuthSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/auth/google/.
    """
    id_token = serializers.CharField(required=True, allow_blank=False)


class SessionSerializer(serializers.ModelSerializer):
    """
    Serializer for Session creation and inspection with robust validation.
    """
    creator = UserSerializer(read_only=True)

    class Meta:
        model = Session
        fields = [
            'id', 'creator', 'title', 'description',
            'starts_at', 'capacity', 'location',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']

    def validate_capacity(self, value):
        if value < 1:
            raise serializers.ValidationError("Capacity must be at least 1.")
        if value > 10000:
            raise serializers.ValidationError("Capacity cannot exceed 10,000.")
        return value

    def validate_starts_at(self, value):
        # On creation (or when changing starts_at), starts_at must be in the future
        if not self.instance or (self.instance and self.instance.starts_at != value):
            if value <= timezone.now():
                raise serializers.ValidationError("Session start time must be in the future.")
        return value


class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for Booking representation.
    """
    user = UserSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'user', 'session', 'status', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
