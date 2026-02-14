from django.utils import timezone
from django.contrib.auth import authenticate, get_user_model
from datetime import timedelta

User = get_user_model()

# Account locking settings
MAX_FAILED_ATTEMPTS =  5
LOCK_DURATION_MINUTES = 30

class AccountLockingService:
    @staticmethod
    def authenticate_with_locking(email: str, password: str):
        """
        Authenticate user with account locking logic
        Returns: (user, error_message, is_locked, status_code)
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None, "Invalid email or password", False, 401

        # Check if account is currently locked
        if user.is_account_locked():
            lock_time_remaining = user.account_locked_until - timezone.now()
            minutes_remaining = max(1, int(lock_time_remaining.total_seconds() / 60))
            return None, f"Account locked. Try again in {minutes_remaining} minutes.", True, 423

        # Try to authenticate
        authenticated_user = authenticate(email=email, password=password)

        if authenticated_user:
            # Successful login - reset failed attempts
            user.reset_failed_attempts()
            return authenticated_user, None, False, 200
        else:
            # Failed login - increment attempts
            user.failed_login_attempts += 1
            user.last_failed_login = timezone.now()

            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                # Lock the account
                user.lock_account(LOCK_DURATION_MINUTES)
                user.save()
                return None, f"Too many failed attempts. Account locked for {LOCK_DURATION_MINUTES} minutes.", True, 423
            else:
                user.save()
                attempts_left = MAX_FAILED_ATTEMPTS - user.failed_login_attempts
                return None, f"Invalid email or password. {attempts_left} attempts remaining.", False, 401

    @staticmethod
    def check_account_status(email: str) -> str:
        """Check if account exists and its lock status"""
        try:
            user = User.objects.get(email=email)
            if user.is_account_locked():
                lock_time_remaining = user.account_locked_until - timezone.now()
                minutes_remaining = max(1, int(lock_time_remaining.total_seconds() / 60))
                return f"Account locked for {minutes_remaining} more minutes"
            return "Account active"
        except User.DoesNotExist:
            return "User not found"