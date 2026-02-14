from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import UserProfile, EmailAddress, UserActivity
from .serializers import (
    UserProfileSerializer,
    EmailAddressSerializer,
    UserActivitySerializer,
    ProfileUpdateSerializer
)
from .forms import ProfileForm, UserUpdateForm, EmailAddressForm
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser]) 
def profile_detail(request):
    """
    API endpoint to get and update user profile (supports both JSON and form-data with images)
    """
    try:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
    except Exception as e:
        logger.error(f"Error getting profile: {str(e)}")
        return Response({"error": "Unable to retrieve profile"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Log activity start
        UserActivity.objects.create(
            user=request.user,
            activity_type='profile_update_start',
            description='Started updating profile',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Check content type to handle both JSON and form-data
        content_type = request.content_type
        
        if 'application/json' in content_type:
            # Handle JSON data
            user_data = request.data.copy()
            profile_data = {}
            
            # Separate user fields from profile fields
            user_fields = ['first_name', 'last_name']
            profile_fields = [
                'nick_name', 'gender', 'country', 'language', 'time_zone',
                'phone_number', 'address', 'city', 'state', 'postal_code',
                'job_title', 'company', 'industry', 'years_of_experience',
                'highest_education', 'university', 'graduation_year', 'bio', 'is_public'
            ]
            
            user_updates = {}
            for field in user_fields:
                if field in user_data:
                    user_updates[field] = user_data[field]
            
            for field in profile_fields:
                if field in user_data:
                    profile_data[field] = user_data[field]
            
            # Update user
            if user_updates:
                for key, value in user_updates.items():
                    setattr(request.user, key, value)
                request.user.save()
            
            # Update profile
            for key, value in profile_data.items():
                setattr(profile, key, value)
            profile.save()
            
        else:
            # Handle form-data (including image upload)
            # Get data for forms
            data = request.data.dict()  # Convert QueryDict to regular dict
            
            # Handle user update
            user_form = UserUpdateForm(data, instance=request.user)
            
            # Handle profile update with files
            profile_form = ProfileForm(data, request.FILES, instance=profile)
            
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                
                # Check if profile picture is being uploaded
                if 'profile_picture' in request.FILES:
                    image_file = request.FILES['profile_picture']
                    
                    # Validate file type
                    allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
                    file_extension = image_file.name.split('.')[-1].lower()
                    
                    if file_extension not in allowed_extensions:
                        return Response(
                            {"error": f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Validate file size (max 5MB)
                    if image_file.size > 5 * 1024 * 1024:
                        return Response(
                            {"error": "File too large. Maximum size is 5MB"},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                profile_form.save()
                
                # Log specific activity if image was uploaded
                if 'profile_picture' in request.FILES:
                    UserActivity.objects.create(
                        user=request.user,
                        activity_type='profile_picture_uploaded',
                        description=f'Uploaded profile picture: {request.FILES["profile_picture"].name}',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
            else:
                errors = {}
                if user_form.errors:
                    errors.update(user_form.errors)
                if profile_form.errors:
                    errors.update(profile_form.errors)
                return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)
        
        # Log successful update
        UserActivity.objects.create(
            user=request.user,
            activity_type='profile_update_success',
            description='Successfully updated profile information',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        serializer = UserProfileSerializer(profile)
        
        # Prepare response
        response_data = {
            "message": "Profile updated successfully",
            "profile": serializer.data
        }
        
        # Add image URL if profile picture exists
        if profile.profile_picture:
            response_data["image_url"] = request.build_absolute_uri(profile.profile_picture.url)
        
        return Response(response_data, status=status.HTTP_200_OK)

# Add the missing profile_update view
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def profile_update(request):
    """
    Alternative endpoint for JSON-only updates
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = ProfileUpdateSerializer(data=request.data)
    
    if serializer.is_valid():
        data = serializer.validated_data
        
        # Update user fields
        if 'first_name' in data:
            request.user.first_name = data['first_name']
        if 'last_name' in data:
            request.user.last_name = data['last_name']
        
        # Update profile fields
        profile_fields = ['nick_name', 'gender', 'country', 'language', 'time_zone', 'phone_number', 'bio']
        for field in profile_fields:
            if field in data:
                setattr(profile, field, data[field])
        
        request.user.save()
        profile.save()
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type='profile_update',
            description='Updated profile via JSON API',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            "message": "Profile updated successfully",
            "profile": UserProfileSerializer(profile).data
        }, status=status.HTTP_200_OK)
    
    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def email_addresses(request):
    """
    API endpoint to manage additional email addresses
    """
    if request.method == 'GET':
        emails = EmailAddress.objects.filter(user=request.user)
        serializer = EmailAddressSerializer(emails, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        form = EmailAddressForm(request.data)
        if form.is_valid():
            email_address = form.save(commit=False)
            email_address.user = request.user
            email_address.verification_sent_at = timezone.now()
            
            # Check if email already exists for any user
            if EmailAddress.objects.filter(email=email_address.email).exists():
                return Response(
                    {"error": "This email address is already registered"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user already has this email
            if EmailAddress.objects.filter(user=request.user, email=email_address.email).exists():
                return Response(
                    {"error": "You have already added this email address"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            email_address.save()
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                activity_type='email_added',
                description=f'Added new email: {email_address.email}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # TODO: Send verification email
            logger.info(f"Verification email should be sent to {email_address.email}")
            
            serializer = EmailAddressSerializer(email_address)
            return Response({
                "message": "Email address added successfully. Please verify your email.",
                "email": serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_email_address(request, email_id):
    """
    API endpoint to delete an additional email address
    """
    try:
        email_address = EmailAddress.objects.get(id=email_id, user=request.user)
        
        # Don't allow deletion of primary email
        if email_address.is_primary:
            return Response(
                {"error": "Cannot delete primary email address"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        email_address.delete()
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type='email_removed',
            description=f'Removed email: {email_address.email}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            "message": "Email address deleted successfully"
        }, status=status.HTTP_200_OK)
    
    except EmailAddress.DoesNotExist:
        return Response(
            {"error": "Email address not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_primary_email(request, email_id):
    """
    API endpoint to set an email as primary
    """
    try:
        email_address = EmailAddress.objects.get(id=email_id, user=request.user)
        
        if not email_address.is_verified:
            return Response(
                {"error": "Email must be verified before setting as primary"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set all user's emails as non-primary
        EmailAddress.objects.filter(user=request.user).update(is_primary=False)
        
        # Set selected email as primary
        email_address.is_primary = True
        email_address.save()
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type='primary_email_changed',
            description=f'Set {email_address.email} as primary email',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            "message": f"{email_address.email} set as primary email"
        }, status=status.HTTP_200_OK)
    
    except EmailAddress.DoesNotExist:
        return Response(
            {"error": "Email address not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_email(request, email_id):
    """
    API endpoint to verify an email address
    """
    try:
        email_address = EmailAddress.objects.get(id=email_id, user=request.user)
        
        # In a real application, you would verify the token sent via email
        # For now, we'll simulate verification
        email_address.is_verified = True
        email_address.save()
        
        # Log activity
        UserActivity.objects.create(
            user=request.user,
            activity_type='email_verified',
            description=f'Verified email: {email_address.email}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            "message": "Email verified successfully"
        }, status=status.HTTP_200_OK)
    
    except EmailAddress.DoesNotExist:
        return Response(
            {"error": "Email address not found"},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_activities(request):
    """
    API endpoint to get user activities
    """
    activities = UserActivity.objects.filter(user=request.user).order_by('-created_at')[:50]
    serializer = UserActivitySerializer(activities, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_summary(request):
    """
    API endpoint to get a summary of user profile
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
    
    summary = {
        "full_name": profile.full_name,
        "email": profile.email,
        "role": request.user.role,
        "profile_picture_url": request.build_absolute_uri(profile.profile_picture.url) if profile.profile_picture else None,
        "job_title": profile.job_title,
        "company": profile.company,
        "email_count": EmailAddress.objects.filter(user=request.user).count(),
        "verified_email_count": EmailAddress.objects.filter(user=request.user, is_verified=True).count(),
        "profile_completion": calculate_profile_completion(profile),
        "last_updated": profile.updated_at,
    }
    
    return Response(summary)


def calculate_profile_completion(profile):
    """
    Calculate profile completion percentage
    """
    fields = [
        profile.nick_name,
        profile.gender,
        profile.country,
        profile.phone_number,
        profile.job_title,
        profile.bio,
        profile.profile_picture,
    ]
    
    completed = sum(1 for field in fields if field)
    total = len(fields)
    
    return int((completed / total) * 100) if total > 0 else 0


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def public_profile(request, user_id=None):
    """
    API endpoint to view public profiles
    """
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            profile = UserProfile.objects.get(user=user)
            
            if not profile.is_public and user != request.user:
                return Response(
                    {"error": "This profile is private"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = UserProfileSerializer(profile)
            return Response(serializer.data)
        
        except (User.DoesNotExist, UserProfile.DoesNotExist):
            return Response(
                {"error": "User profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Return current user's profile
    profile = get_object_or_404(UserProfile, user=request.user)
    serializer = UserProfileSerializer(profile)
    return Response(serializer.data)