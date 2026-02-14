from django import forms
from django.contrib.auth import get_user_model
from .models import UserProfile, EmailAddress

User = get_user_model()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'nick_name',
            'gender',
            'country',
            'language',
            'time_zone',
            'phone_number',
            'address',
            'city',
            'state',
            'postal_code',
            'job_title',
            'company',
            'industry',
            'years_of_experience',
            'highest_education',
            'university',
            'graduation_year',
            'profile_picture',
            'bio',
            'is_public',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'time_zone': forms.Select(attrs={'class': 'form-select'}),
        }


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']


class EmailAddressForm(forms.ModelForm):
    class Meta:
        model = EmailAddress
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'placeholder': 'Enter additional email address',
                'class': 'form-control'
            })
        }