import io
from django.urls import reverse
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from cv_manager.models import UploadedResume

#_________________these are the test cases for the resume upload api _____________________________________

class ResumeUploadAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.upload_url = reverse("resume_upload")  
        self.success_url = reverse("upload_success")

    def test_no_file_uploaded(self):
        response = self.client.post(self.upload_url, {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No file uploaded.")

    def test_invalid_file_format(self):
        invalid_file = SimpleUploadedFile("test.txt", b"dummy content")
        response = self.client.post(self.upload_url, {"file": invalid_file})
        self.assertEqual(response.status_code, 200)
        # updated to match backend message
        self.assertContains(
            response,
            "Invalid file type. Only PDF and DOCX allowed."
        )
<<<<<<< HEAD

=======
>>>>>>> 434fd985b534d825f643b615b27bc04169e463e8
    def test_large_file_rejected(self):
        large_content = b"x" * (5 * 1024 * 1024 + 1)  # 5MB + 1 byte
        large_file = SimpleUploadedFile("large.pdf", large_content)
        response = self.client.post(self.upload_url, {"file": large_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "File size exceeds 5MB.")

    def test_successful_upload(self):
        file_content = b"dummy pdf content"
        file = SimpleUploadedFile("resume.pdf", file_content, content_type="application/pdf")
        response = self.client.post(self.upload_url, {"file": file})
        self.assertRedirects(response, self.success_url)

        # Check DB
        resume = UploadedResume.objects.first()
        self.assertIsNotNone(resume)
        self.assertEqual(resume.original_name, "resume.pdf")
        self.assertEqual(resume.size, len(file_content))
