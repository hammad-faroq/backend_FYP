from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token

from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.conf import settings
from django.utils.timezone import now
from datetime import timedelta

import random
import string

from .services.auth_service import AccountLockingService
import os 
from postmarker.core import PostmarkClient

User = get_user_model()

# ─────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────

def generate_otp(length=6):
    """Generate a secure 6-digit numeric OTP."""
    return ''.join(random.choices(string.digits, k=length))


# ─────────────────────────────────────────────────────────────
# API-01: REGISTER
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    data = request.data
    required_fields = ['first_name', 'last_name', 'email', 'password', 'role']

    for field in required_fields:
        if not data.get(field):
            return Response({"error": f"{field} is required"}, status=status.HTTP_400_BAD_REQUEST)

    if data['role'] not in ['job_seeker', 'hr']:
        return Response({"error": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=data['email']).exists():
        return Response({"error": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        email=data['email'],
        password=data['password'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        role=data['role']
    )

    return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
import os
import requests as http_requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from user_profile.models import UserProfile

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    access_token = request.data.get('access_token')
    role = request.data.get('role')  # ← new

    if not access_token:
        return Response({"error": "access_token is required"}, status=400)

    resp = http_requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if resp.status_code != 200:
        return Response({"error": "Invalid Google token"}, status=401)

    info = resp.json()
    email = info.get('email')
    first_name = info.get('given_name', '')
    last_name = info.get('family_name', '')
    picture = info.get('picture', '')

    if not email:
        return Response({"error": "Email not provided by Google"}, status=400)

    # Check if user already exists
    existing_user = User.objects.filter(email=email).first()

    if existing_user:
        # Existing user — just log them in
        token, _ = Token.objects.get_or_create(user=existing_user)
        return Response({
            "token": token.key,
            "user_id": existing_user.id,
            "role": existing_user.role,
            "is_superuser": existing_user.is_superuser,
            "first_name": existing_user.first_name,
            "picture": picture,
            "needs_role": False,
        })
    
    # New user — if no role provided, ask frontend to collect it
    if not role:
        return Response({
            "needs_role": True,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "picture": picture,
            "access_token": access_token,  # pass back so frontend can resend
        })

    if role not in ['job_seeker', 'hr']:
        return Response({"error": "Invalid role"}, status=400)

    # Create new user with chosen role
    user = User.objects.create_user(
        email=email,
        password=None,
        first_name=first_name,
        last_name=last_name,
        role=role,
    )
    user.set_unusable_password()
    user.save()

    if picture:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if not profile.profile_picture:
            profile.google_picture_url = picture
            profile.save()

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "token": token.key,
        "user_id": user.id,
        "role": user.role,
        "is_superuser": user.is_superuser,
        "first_name": user.first_name,
        "picture": picture,
        "needs_role": False,
    })


# ─────────────────────────────────────────────────────────────
# API-NEW-01: SEND OTP  →  POST /auth/send-otp/
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# API-06: PASSWORD RESET
# ─────────────────────────────────────────────────────────────


@api_view(['POST'])
@permission_classes([AllowAny])
def api_send_otp(request):
    email = request.data.get('email', '').strip().lower()

    if not email:
        return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=email).exists():
        return Response({"error": "An account with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

    rate_key = f"otp_rate_{email}"
    if cache.get(rate_key):
        return Response(
            {"error": "Please wait 60 seconds before requesting a new OTP."},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    otp = generate_otp()
    cache_key = f"otp_{email}"
    cache.set(cache_key, otp, timeout=300)
    cache.set(rate_key, True, timeout=60)

    try:
        postmark = PostmarkClient(server_token=settings.POSTMARK_SERVER_TOKEN)
        postmark.emails.send(
            From=settings.POSTMARK_SENDER,
            To=email,
            Subject='Your TalentMatch AI Verification Code',
            TextBody=f"""Hello,

                    Your verification code is: {otp}

                    This code expires in 5 minutes.
                    If you did not request this, ignore this email.

                    — TalentMatch AI Team"""
        )
    except Exception as e:
        cache.delete(cache_key)
        cache.delete(rate_key)
        return Response(
            {"error": f"Email failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response({"message": "OTP sent successfully."}, status=status.HTTP_200_OK)



# def api_send_otp(request):
#     """
#     Generates a 6-digit OTP, stores it in Django cache for 5 minutes,
#     and emails it to the user.
#     Called BEFORE registration — email must NOT already exist.
#     """
#     email = request.data.get('email', '').strip().lower()

#     if not email:
#         return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

#     # Block if email is already registered
#     if User.objects.filter(email=email).exists():
#         return Response({"error": "An account with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)

#     # Rate limiting: block if OTP was sent less than 60 seconds ago
#     rate_key = f"otp_rate_{email}"
#     if cache.get(rate_key):
#         return Response(
#             {"error": "Please wait 60 seconds before requesting a new OTP."},
#             status=status.HTTP_429_TOO_MANY_REQUESTS
#         )

#     # Generate and store OTP (expires in 5 minutes = 300 seconds)
#     otp = generate_otp()
#     cache_key = f"otp_{email}"
#     cache.set(cache_key, otp, timeout=300)

#     # Set rate-limit flag for 60 seconds
#     cache.set(rate_key, True, timeout=60)

#     # Send email
#     try:
#         send_mail(
#             subject="Your TalentMatch AI Verification Code",
#             message=(
#                 f"Hello,\n\n"
#                 f"Your verification code is: {otp}\n\n"
#                 f"This code expires in 5 minutes.\n"
#                 f"If you did not request this, please ignore this email.\n\n"
#                 f"— TalentMatch AI Team"
#             ),
#             from_email=None,   # Uses DEFAULT_FROM_EMAIL from settings.py
#             recipient_list=[email],
#             fail_silently=False,
#         )
#     except Exception as e:
#         # Clean up cache if email fails so user can retry
#         cache.delete(cache_key)
#         cache.delete(rate_key)
#         return Response(
#             {"error": "Failed to send email. Please try again."},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )

#     return Response({"message": "OTP sent successfully."}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# API-NEW-02: VERIFY OTP  →  POST /auth/verify-otp/
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def api_verify_otp(request):
    """
    Verifies the OTP entered by the user.
    On success, deletes the OTP from cache so it can't be reused.
    The frontend then calls /register/ immediately after.
    """
    email = request.data.get('email', '').strip().lower()
    otp_input = request.data.get('otp', '').strip()

    if not email or not otp_input:
        return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

    cache_key = f"otp_{email}"
    stored_otp = cache.get(cache_key)

    if stored_otp is None:
        return Response(
            {"error": "OTP has expired. Please request a new one."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if stored_otp != otp_input:
        return Response(
            {"error": "Invalid OTP. Please check the code and try again."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # OTP is correct — delete it so it can't be reused
    cache.delete(cache_key)

    return Response({"message": "OTP verified successfully."}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# API-02: LOGIN
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    user, error_message, is_locked, status_code = AccountLockingService.authenticate_with_locking(email, password)

    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "message": "Login successful",
            "token": token.key,
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "is_superuser": user.is_superuser
        }, status=status.HTTP_200_OK)
    else:
        return Response({"error": error_message, "locked": is_locked}, status=status_code)


# ─────────────────────────────────────────────────────────────
# API-03: DASHBOARD
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
# API-04: LOGOUT
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    request.user.auth_token.delete()
    return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# API-05: ACCOUNT STATUS
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def api_check_account_status(request):
    email = request.data.get("email")
    if not email:
        return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

    status_message = AccountLockingService.check_account_status(email)
    return Response({"status": status_message}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# API-06: PASSWORD RESET
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def api_password_reset_request(request):
    email = request.data.get('email')
    if not email:
        return Response({"error": "Email is required"}, status=400)

    # ✅ Rate limit: max 2 password reset emails per day per email
    rate_key = f"pwd_reset_rate_{email}"
    attempts = cache.get(rate_key, 0)
    if attempts >= 2:
        return Response(
            {"error": "You can only request 2 password resets per day. Please try again tomorrow."},
            status=429
        )

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "No user with this email"}, status=404)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    cache_key = f"pwd_reset_{uid}"
    cache.set(cache_key, True, timeout=3600)

    reset_link = f"{settings.API_BASE}/password-reset-confirm/{uid}/{token}/"

    postmark = PostmarkClient(server_token=settings.POSTMARK_SERVER_TOKEN)
    postmark.emails.send(
            From=settings.POSTMARK_SENDER,
            To=email,
            Subject='Password Reset Request — TalentMatch AI',
            TextBody=(
                f"Click this link to reset your password:\n\n{reset_link}\n\nThis link expires in 1 hour."
            )
        )

    # send_mail(
    #     subject="Password Reset Request — TalentMatch AI",
    #     message=f"Click this link to reset your password:\n\n{reset_link}\n\nThis link expires in 1 hour.",
    #     from_email=None,
    #     recipient_list=[user.email],
    #     fail_silently=False,
    # )

    # ✅ Increment counter, expires at midnight (seconds until end of day)
    from django.utils.timezone import now
    seconds_until_midnight = 86400 - (now().hour * 3600 + now().minute * 60 + now().second)
    cache.set(rate_key, attempts + 1, timeout=seconds_until_midnight)

    return Response({"message": "Password reset email sent"}, status=200)


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
    cache_key = f"pwd_reset_{uidb64}"

    if not cache.get(cache_key):
        return Response(
            {"error": "Link expired. Please request a new password reset."},
            status=400
        )

    user.set_password(new_password)
    user.save()
    return Response({"message": "Password reset successful"}, status=200)


# ─────────────────────────────────────────────────────────────
# API-07: CHANGE PASSWORD
# ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_change_password(request):
    user = request.user
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')

    if not all([current_password, new_password, confirm_password]):
        return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)

    if not user.check_password(current_password):
        return Response({"error": "Current password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

    if new_password != confirm_password:
        return Response({"error": "New passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

    if current_password == new_password:
        return Response({"error": "New password must be different from current password"}, status=status.HTTP_400_BAD_REQUEST)

    if len(new_password) < 8:
        return Response({"error": "Password must be at least 8 characters"}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()

    Token.objects.filter(user=user).delete()
    new_token = Token.objects.create(user=user)

    return Response({
        "message": "Password changed successfully",
        "token": new_token.key
    }, status=status.HTTP_200_OK)