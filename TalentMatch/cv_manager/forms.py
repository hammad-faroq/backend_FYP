from django import forms
from .models import ResumeTemplate1,ResumeTemplate2
import os, uuid

class ResumeTemplate1Form(forms.ModelForm):
    class Meta:
        model = ResumeTemplate1
        fields = ['full_name', 'profession', 'email', 'linkedin', 'phone', 
                 'profile', 'interests', 'additional_info', 'profile_image','github']
        widgets = {
            'profile_image': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def clean_profile_image(self):
        image = self.cleaned_data.get("profile_image")

        if image:
            # --- Validate size (max 5MB) ---
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Image size must be less than 5MB.")

            # --- Validate MIME type ---
            if not image.content_type.startswith("image/"):
                raise forms.ValidationError("Invalid file type. Only images are allowed.")

            # --- Rename file safely ---
            ext = os.path.splitext(image.name)[1]  # get original extension (.jpg, .png, etc.)
            image.name = f"{uuid.uuid4().hex}{ext}"  # assign new UUID filename

        return image


# ----------------------#
# ----Temaplate 2-------#
# ----------------------#


class ResumeTemplate2Form(forms.ModelForm):
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))
    # summary = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}))
    
    class Meta:
        model = ResumeTemplate2
        fields = [
            "full_name", "address", "phone", "email",
            "linkedin", "github"
        ]
        widgets = {
            'linkedin': forms.URLInput(attrs={'placeholder': 'https://linkedin.com/in/yourprofile'}),
            'github': forms.URLInput(attrs={'placeholder': 'https://github.com/yourusername'}),
        }