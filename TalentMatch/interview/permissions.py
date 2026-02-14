from rest_framework import permissions

class IsHRUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_hr()

class IsCandidate(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_job_seeker()

class IsInterviewParticipant(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'candidate') and hasattr(obj, 'hr_user'):
            return request.user in [obj.candidate, obj.hr_user]
        return False