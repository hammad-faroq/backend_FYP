# interviews/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.exceptions import ValidationError, PermissionDenied
import json
import traceback

class InterviewErrorMiddleware(MiddlewareMixin):
    """Middleware to handle interview-specific errors"""
    
    def process_exception(self, request, exception):
        # Handle specific interview errors
        error_handlers = {
            'ValidationError': self._handle_validation_error,
            'PermissionDenied': self._handle_permission_error,
            'InterviewNotStarted': self._handle_interview_not_started,
            'InterviewExpired': self._handle_interview_expired,
            'AnswerAlreadySubmitted': self._handle_answer_submitted,
        }
        
        # Check for custom interview exceptions
        exception_name = exception.__class__.__name__
        
        if exception_name in error_handlers:
            return error_handlers[exception_name](exception)
        
        # Log unexpected errors
        if exception_name not in ['Http404', 'CSRFError']:
            print(f"Unhandled interview error: {exception}")
            traceback.print_exc()
        
        return None
    
    def _handle_validation_error(self, exception):
        return JsonResponse({
            'error': 'Validation Error',
            'details': exception.message_dict if hasattr(exception, 'message_dict') else str(exception),
            'type': 'validation'
        }, status=400)
    
    def _handle_permission_error(self, exception):
        return JsonResponse({
            'error': 'Permission Denied',
            'message': 'You do not have permission to perform this action',
            'type': 'permission',
            'required_role': 'HR' if 'hr' in str(exception).lower() else 'Candidate'
        }, status=403)
    
    def _handle_interview_not_started(self, exception):
        return JsonResponse({
            'error': 'Interview Not Started',
            'message': 'The interview has not started yet',
            'type': 'interview_state',
            'action': 'wait_or_contact_hr'
        }, status=400)
    
    def _handle_interview_expired(self, exception):
        return JsonResponse({
            'error': 'Interview Expired',
            'message': 'The interview time has expired',
            'type': 'interview_state',
            'action': 'contact_hr_for_reschedule'
        }, status=400)
    
    def _handle_answer_submitted(self, exception):
        return JsonResponse({
            'error': 'Answer Already Submitted',
            'message': 'You have already submitted an answer for this question',
            'type': 'answer_state',
            'action': 'view_submitted_answer'
        }, status=400)

# Custom exceptions
class InterviewNotStarted(Exception):
    pass

class InterviewExpired(Exception):
    pass

class AnswerAlreadySubmitted(Exception):
    pass

class SchedulingConflict(Exception):
    pass

class InsufficientQuestions(Exception):
    pass