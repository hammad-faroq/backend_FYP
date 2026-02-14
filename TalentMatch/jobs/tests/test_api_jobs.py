from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from jobs.models import JobPosting
from rest_framework.authtoken.models import Token
from datetime import date, timedelta

User = get_user_model()

class JobPostingAPITests(APITestCase):
    def setUp(self):
        # Create normal user
        self.user = User.objects.create_user(
            email="normaluser@example.com",
            password="test123",
            role="job_seeker"
        )
        # Create HR user
        self.hr_user = User.objects.create_user(
            email="hruser@example.com",
            password="test123",
            role="hr",
            is_staff=True
        )

        # Create tokens for authentication
        self.user_token = Token.objects.create(user=self.user)
        self.hr_token = Token.objects.create(user=self.hr_user)

        self.client = APIClient()
        self.list_url = reverse('jobposting-list')  # from router

        self.valid_payload = {
            "title": "Backend Engineer",
            "description": "Work on APIs",
            "application_deadline": (date.today() + timedelta(days=5)).isoformat()
        }

    def authenticate(self, user_type='hr'):
        """Helper to set token auth for client"""
        if user_type == 'hr':
            self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.hr_token.key)
        else:
            self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user_token.key)

    def test_list_jobs(self):
        """Anyone can list jobs"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_job_as_hr(self):
        """HR user can create job"""
        self.authenticate(user_type='hr')
        response = self.client.post(self.list_url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(JobPosting.objects.count(), 1)

    def test_create_job_as_normal_user_forbidden(self):
        """Normal user should NOT create job"""
        self.authenticate(user_type='normal')
        response = self.client.post(self.list_url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_validation_deadline_in_past(self):
        """Reject jobs with past deadline"""
        self.authenticate(user_type='hr')
        bad_payload = {
            "title": "Expired Job",
            "description": "Invalid test",
            "application_deadline": (date.today() - timedelta(days=1)).isoformat()
        }
        response = self.client.post(self.list_url, bad_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_job_as_hr(self):
        """HR can update job"""
        self.authenticate(user_type='hr')
        job = JobPosting.objects.create(
            title="Old Title",
            description="Old desc",
            application_deadline=date.today() + timedelta(days=3),
            created_by=self.hr_user
        )
        url = reverse('jobposting-detail', args=[job.id])
        response = self.client.patch(url, {"title": "New Title"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        job.refresh_from_db()
        self.assertEqual(job.title, "New Title")

    def test_delete_job_as_hr(self):
        """HR can delete job"""
        self.authenticate(user_type='hr')
        job = JobPosting.objects.create(
            title="To Delete",
            description="delete me",
            application_deadline=date.today() + timedelta(days=3),
            created_by=self.hr_user
        )
        url = reverse('jobposting-detail', args=[job.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(JobPosting.objects.count(), 0)
