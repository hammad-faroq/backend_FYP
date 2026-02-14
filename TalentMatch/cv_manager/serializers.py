
from rest_framework import serializers
from .models import UploadedResume, ParsedResume

class UploadedResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedResume
        fields = ["id", "file", "original_name", "size", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at", "size", "original_name"]

    def validate_file(self, file):
        max_size = 5 * 1024 * 1024  # 5 MB
        if file.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 5MB.")
        return file

class UploadedResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedResume
        fields = "__all__"


class ParsedResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParsedResume
        fields = "__all__"
