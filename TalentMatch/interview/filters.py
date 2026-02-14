from django_filters import rest_framework as filters
from .models import Interview, InterviewQuestion

class InterviewFilter(filters.FilterSet):
    status = filters.CharFilter(lookup_expr='iexact')
    interview_type = filters.CharFilter(lookup_expr='iexact')
    scheduled_date_after = filters.DateTimeFilter(field_name='scheduled_date', lookup_expr='gte')
    scheduled_date_before = filters.DateTimeFilter(field_name='scheduled_date', lookup_expr='lte')
    hr_user = filters.NumberFilter(field_name='hr_user_id')
    candidate = filters.NumberFilter(field_name='candidate_id')

    class Meta:
        model = Interview
        fields = ['status', 'interview_type', 'scheduled_date_after', 'scheduled_date_before', 'hr_user', 'candidate']

class InterviewQuestionFilter(filters.FilterSet):
    difficulty = filters.CharFilter(lookup_expr='iexact')
    category = filters.NumberFilter(field_name='category_id')
    question_type = filters.CharFilter(lookup_expr='iexact')
    is_mine = filters.BooleanFilter(method='filter_is_mine')
    
    class Meta:
        model = InterviewQuestion
        fields = ['difficulty', 'category', 'question_type']
    
    def filter_is_mine(self, queryset, name, value):
        if value:
            return queryset.filter(created_by=self.request.user)
        return queryset