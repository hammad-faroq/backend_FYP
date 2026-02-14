from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token

# new imports for the last 2 views 

from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from .services.auth_service import AccountLockingService  # <-- fixed import

User = get_user_model()

# ------------------ API-01: REGISTER ---------------


# @csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    data = request.data
    required_fields = ['first_name', 'last_name', 'email', 'password', 'role']

    # Check missing fields
    for field in required_fields:
        if not data.get(field):
            return Response({"error": f"{field} is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Validate role
    if data['role'] not in ['job_seeker', 'hr']:
        return Response({"error": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)

    # Check email uniqueness
    if User.objects.filter(email=data['email']).exists():
        return Response({"error": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST)

    # Create user
    user = User.objects.create_user(
        email=data['email'],
        password=data['password'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        role=data['role']
    )

    return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)


# ------------------ API-02: LOGIN (Enhanced with Account Locking) ------------------


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    # Use account locking service
    user, error_message, is_locked, status_code = AccountLockingService.authenticate_with_locking(email, password)

    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "message": "Login successful",
            "token": token.key,
            "user_id": user.id,          # ✅ Added
            "email": user.email,
            "role": user.role,
            "is_superuser": user.is_superuser
        }, status=status.HTTP_200_OK)
    else:
        response_data = {
            "error": error_message,
            "locked": is_locked
        }
        return Response(response_data, status=status_code)


# ------------------ API-03: DASHBOARD ------------------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_dashboard(request):
    user = request.user
    if user.is_superuser:
        message = "Welcome Admin"
    elif user.role == "hr":
        message = "Welcome HR"
    elif user.role == "job_seeker":
        message = "Welcome Job Seeker"
    else:
        message = "Welcome User"

    return Response({
        "message": message,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role
    })


# ------------------ API-04: LOGOUT ------------------


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    # Delete the user's token so it can't be reused
    request.user.auth_token.delete()
    return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)



# ------------------ API-05: Check Account Status (New for Task 1.7) ------------------


@api_view(['POST'])
@permission_classes([AllowAny])
def api_check_account_status(request):
    email = request.data.get("email")
    if not email:
        return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    status_message = AccountLockingService.check_account_status(email)
    return Response({"status": status_message}, status=status.HTTP_200_OK)

# ---------------------- API-06: Password reset email and token views ----------------------


# Request password reset (send email)
@api_view(['POST'])
@permission_classes([AllowAny])
def api_password_reset_request(request):
    email = request.data.get('email')
    if not email:
        return Response({"error": "Email is required"}, status=400)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "No user with this email"}, status=404)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_link = f"http://localhost:3000/password-reset-confirm/{uid}/{token}/"

    # Send email (for dev you can print in console)
    send_mail(
        "Password Reset Request",
        f"Click this link to reset your password: {reset_link}",
        "no-reply@talentmatch.ai",
        [user.email],
        fail_silently=False,
    )

    return Response({"message": "Password reset email sent"}, status=200)


# Confirm password reset (set new password)
@api_view(['POST'])
@permission_classes([AllowAny])
def api_password_reset_confirm(request, uidb64, token):
    new_password = request.data.get("password")
    if not new_password:
        return Response({"error": "Password is required"}, status=400)

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({"error": "Invalid link"}, status=400)

    if not default_token_generator.check_token(user, token):
        return Response({"error": "Invalid or expired token"}, status=400)

    user.set_password(new_password)
    user.save()
    return Response({"message": "Password reset successful"}, status=200)