from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta


# -------------------------
# Manager Class (Encapsulates Creation Logic)
# -------------------------
class UserManager(BaseUserManager):
    """
    Custom manager for User model with methods to create
    normal users and superusers separately.
    """

    def create_user(self, email: str, password: str = None, role: str = None, **extra_fields):
        # sourcery skip: class-extract-method
        """
        Creates and saves a normal user with the given email, password, and role.
        """
        if not email:
            raise ValueError("Email is required.")
        if role not in ['job_seeker', 'hr']:
            raise ValueError("Role must be either 'job_seeker' or 'hr'.")

        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str = None, **extra_fields):
        """
        Creates and saves a superuser with full permissions.
        Superuser does not belong to 'job_seeker' or 'hr' roles.
        """
        if not email:
            raise ValueError("Email is required.")

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        # Ensure superuser has required fields
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        superuser = self.model(email=self.normalize_email(email), **extra_fields)
        superuser.set_password(password)
        superuser.save(using=self._db)
        return superuser


# -------------------------
# User Model Class
# -------------------------
class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model that supports email authentication and role-based access.
    """

    # ---- Class Variables ----
    ROLE_CHOICES = (
        ('job_seeker', 'Job Seeker'),
        ('hr', 'HR'),
    )

    # ---- Fields ----
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        blank=True,  # Allowed for superuser
        null=True,
    )
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    # Django Permissions fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Task 1.7: Account locking fields
    failed_login_attempts = models.IntegerField(default=0)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    account_locked_until = models.DateTimeField(null=True, blank=True)

    # ---- Manager ----
    objects = UserManager()

    # ---- Authentication Settings ----
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    # ---- String Representation ----
    def __str__(self) -> str:
        return f"{self.email} ({self.get_role_display() if self.role else 'Superuser'})"

    # ---- Business Logic ----
    def is_job_seeker(self) -> bool:
        """Check if user is a Job Seeker."""
        return self.role == 'job_seeker'

    def is_hr(self) -> bool:
        """Check if user is an HR."""
        return self.role == 'hr'

    # ---- Task 1.7: Account Locking Methods ----
    def is_account_locked(self) -> bool:
        """Check if account is currently locked"""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False

    def lock_account(self, duration_minutes: int = 10) -> None:
        """Lock account for specified duration"""
        self.account_locked_until = timezone.now() + timedelta(minutes=duration_minutes)
        self.save()

    def reset_failed_attempts(self) -> None:
        """Reset failed login attempts counter"""
        self.failed_login_attempts = 0
        self.last_failed_login = None
        self.account_locked_until = None
        self.save()