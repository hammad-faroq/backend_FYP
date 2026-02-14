from rest_framework import serializers
from .models import (
    Interview, InterviewQuestion, InterviewCategory,
    CandidateAnswer, PreparationModule, UserPreparationProgress,
    InterviewQuestionSet, AvailabilitySlot
)

# -------------------------------
# Interview Category Serializer
# -------------------------------
class InterviewCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewCategory
        fields = ['id', 'name', 'description', 'icon', 'is_active']
        read_only_fields = ['id']

    def create(self, validated_data):
        user = self.context['request'].user
        return InterviewCategory.objects.create(created_by=user, **validated_data)


# -------------------------------
# Bulk Interview Question Serializer
# -------------------------------
class BulkInterviewQuestionSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        user = self.context['request'].user
        questions = [InterviewQuestion.objects.create(created_by=user, **item) for item in validated_data]
        return questions


# -------------------------------
# Interview Question Serializer
# -------------------------------
class InterviewQuestionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=InterviewCategory.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = InterviewQuestion
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']
        list_serializer_class = BulkInterviewQuestionSerializer

    def validate(self, data):
        qt = data['question_type']
        auto_score = data.get('auto_score_enabled', False)  # default False if not provided

        if qt.id == 1:  # MCQ
            if auto_score:
                if not data.get('options'):
                    raise serializers.ValidationError({"options": "MCQ questions require options for auto scoring"})
                if not data.get('correct_option_indices'):
                    raise serializers.ValidationError({"correct_option_indices": "MCQ questions require correct_option_indices for auto scoring"})
        else:  # Descriptive
            if auto_score:
                if not data.get('keywords'):
                    raise serializers.ValidationError({"keywords": "Descriptive questions require keywords for auto scoring"})
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        return InterviewQuestion.objects.create(created_by=user, **validated_data)



# -------------------------------
# Interview Serializer
# -------------------------------
class InterviewSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.get_full_name', read_only=True)
    hr_name = serializers.CharField(source='hr_user.get_full_name', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    candidate_email = serializers.EmailField(source='candidate.email', read_only=True)
    categories = serializers.PrimaryKeyRelatedField(
        queryset=InterviewCategory.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Interview
        fields = [
            'id', 'candidate', 'hr_user', 'job', 'status', 'created_at', 'updated_at',
            'candidate_name', 'hr_name', 'job_title', 'categories','candidate_email'
        ]
        read_only_fields = [
            'candidate', 'job', 'hr_user', 'status', 'created_at', 'updated_at','candidate_email'
        ]


# -------------------------------
# Interview Question Set Serializer
# -------------------------------
class InterviewQuestionSetSerializer(serializers.ModelSerializer):
    question_details = InterviewQuestionSerializer(source='question', read_only=True)

    class Meta:
        model = InterviewQuestionSet
        fields = [
            'id', 'interview', 'question', 'order', 'required',
            'expected_answer_text', 'expected_keywords', 'auto_score_enabled',
            'question_details',
        ]


# -------------------------------
# Interview Detail Serializer
# -------------------------------
class InterviewDetailSerializer(InterviewSerializer):
    question_sets = InterviewQuestionSetSerializer(many=True, read_only=True)

    class Meta(InterviewSerializer.Meta):
        fields = InterviewSerializer.Meta.fields + ['question_sets']


# -------------------------------
# Candidate Answer Serializer
# -------------------------------
class CandidateAnswerSerializer(serializers.ModelSerializer):
    question = serializers.CharField(source='question_set.question.question_text', read_only=True)

    class Meta:
        model = CandidateAnswer
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'auto_score', 'graded_at']

    def validate(self, data):
        question = data['question_set'].question
        if question.question_type == 'mcq' and not data.get('selected_options'):
            raise serializers.ValidationError("MCQ questions require selected_options")
        return data


# -------------------------------
# Preparation Module Serializer
# -------------------------------
class PreparationModuleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = PreparationModule
        fields = '__all__'


# -------------------------------
# User Preparation Progress Serializer
# -------------------------------
class UserPreparationProgressSerializer(serializers.ModelSerializer):
    module_title = serializers.CharField(source='module.title', read_only=True)

    class Meta:
        model = UserPreparationProgress
        fields = '__all__'


# -------------------------------
# Availability Slot Serializer
# -------------------------------
class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = '__all__'


# -------------------------------
# Candidate Answer Review Serializer
# -------------------------------
class CandidateAnswerReviewSerializer(serializers.ModelSerializer):
    question_text = serializers.SerializerMethodField()
    candidate_name = serializers.CharField(source='candidate.get_full_name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)

    class Meta:
        model = CandidateAnswer
        fields = [
            'id', 'candidate', 'candidate_name', 'candidate_email',
            'question_set', 'question_text', 'answer_text',
            'selected_options', 'code_snippet', 'file_upload',
            'auto_score', 'hr_score', 'hr_feedback', 'is_submitted', 'submitted_at', 'graded_at'
        ]
        read_only_fields = fields

    def get_question_text(self, obj):
        if obj.question_set and obj.question_set.question:
            return obj.question_set.question.question_text
        return None


# -------------------------------
# Interview Result Serializer
# -------------------------------
class InterviewResultSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.get_full_name', read_only=True)
    hr_name = serializers.CharField(source='hr_user.get_full_name', read_only=True)
    answers = serializers.SerializerMethodField()

    class Meta:
        model = Interview
        fields = ['id', 'candidate', 'candidate_name', 'hr_user', 'hr_name', 'status', 'answers']

    def get_answers(self, obj):
        from .models import CandidateAnswer
        answers = CandidateAnswer.objects.filter(question_set__interview=obj)
        return CandidateAnswerReviewSerializer(answers, many=True).data