from rest_framework import permissions

class IsHROrReadOnly(permissions.BasePermission):
    """
    - Job seekers: read-only
    - HR: create/update/delete their own jobs
    """
    
    def has_permission(self, request, view):
        # Anyone can read
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only authenticated HR can create/update/delete
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'hr'

    def has_object_permission(self, request, view, obj):
        # Safe methods: anyone can read
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only HR who created the job can update/delete
        return (
            request.user.is_authenticated and 
            getattr(request.user, 'role', None) == 'hr' and 
            obj.created_by == request.user
        )