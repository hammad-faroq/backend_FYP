# interview/bulk_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .serializers import InterviewQuestionSerializer
from .permissions import IsHRUser

class BulkInterviewQuestionCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHRUser]

    def post(self, request):
        questions = request.data.get("questions")

        if not isinstance(questions, list) or not questions:
            return Response(
                {"error": "'questions' must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = InterviewQuestionSerializer(
            data=questions,
            many=True,
            context={"request": request}
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": True,
                "created": len(serializer.data),
                "questions": serializer.data
            },
            status=status.HTTP_201_CREATED
        )