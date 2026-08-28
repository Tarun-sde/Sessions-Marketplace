from rest_framework import permissions


class IsCreator(permissions.BasePermission):
    """
    Permission check: Allows access only to authenticated users who are creators (is_creator=True).
    """
    message = "Only registered creators can create sessions."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_creator
        )


class IsSessionOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow creators of a session to edit or delete it.
    Authenticated users can read (GET/HEAD/OPTIONS).
    """
    message = "You can only edit or delete sessions that you created."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            request.user and
            request.user.is_authenticated and
            obj.creator_id == request.user.id
        )


class IsBookingOwner(permissions.BasePermission):
    """
    Object-level permission to only allow the owner of a booking to access or cancel it.
    """
    message = "You can only manage your own bookings."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user and
            request.user.is_authenticated and
            obj.user_id == request.user.id
        )
