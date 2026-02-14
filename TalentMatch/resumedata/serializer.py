from rest_framework import serializers
from resumedata.models import ResumeData


class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeData
        fields = "__all__"
