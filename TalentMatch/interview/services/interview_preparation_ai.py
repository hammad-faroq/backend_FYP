import os
import json
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY missing")


class InterviewPreparationGenerator:
    """
    Generates interview preparation material for job seekers
    based on the job description they applied for.
    """

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = "llama-3.1-8b-instant"

    def generate_preparation(
        self,
        job_title: str,
        job_description: str,
        company_name: str = ""
    ) -> dict:
        """
        Generate interview questions + answers for job preparation
        """
        prompt = f"""
You are a senior technical interviewer and professional career coach.

JOB TITLE:
{job_title}

COMPANY:
{company_name or "Not specified"}

JOB DESCRIPTION:
{job_description}

TASK:
Create a COMPLETE interview preparation guide for a job candidate.

RETURN STRICT JSON ONLY in this format:

{{
  "technical_questions": [
    {{"question": "string", "ideal_answer": "string"}}
  ],
  "behavioral_questions": [
    {{"question": "string", "sample_answer": "string"}}
  ],
  "scenario_questions": [
    {{"scenario": "string", "expected_approach": "string"}}
  ],
  "common_mistakes": ["string"],
  "quick_revision_notes": ["string"]
}}

RULES:
- Questions must be realistic interview questions
- Answers must be concise but strong
- No filler text
- Assume junior-to-mid level candidate
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()
            return json.loads(content)

        except Exception as e:
            logger.error(f"Interview prep generation failed: {str(e)}")
            return {
                "technical_questions": [],
                "behavioral_questions": [],
                "scenario_questions": [],
                "common_mistakes": [],
                "quick_revision_notes": [],
                "error": "Interview preparation generation failed"
            }

    # -----------------------------------------
    # ✅ Generate more questions
    # -----------------------------------------
    def generate_more_questions(self, job_title: str, job_description: str) -> dict:
        """
        Generate additional interview questions only
        """
        prompt = f"""
You are a senior technical interviewer.

JOB TITLE:
{job_title}

JOB DESCRIPTION:
{job_description}

TASK:
Generate 3-5 additional interview questions (technical, behavioral, or scenario) that a junior-to-mid level candidate may encounter.

RETURN STRICT JSON ONLY in this format:

{{
  "technical_questions": [{{"question": "string", "ideal_answer": "string"}}],
  "behavioral_questions": [{{"question": "string", "sample_answer": "string"}}],
  "scenario_questions": [{{"scenario": "string", "expected_approach": "string"}}]
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content.strip()
            return json.loads(content)

        except Exception as e:
            logger.error(f"Generate more questions failed: {str(e)}")
            return {
                "technical_questions": [],
                "behavioral_questions": [],
                "scenario_questions": [],
                "error": "Failed to generate more questions"
            }

    # -----------------------------------------
    # ✅ Chat reply (mock interview)
    # -----------------------------------------
    def chat_reply(self, job_title: str, job_description: str, chat_history: list) -> str:
        """
        Generate AI reply for mock interview chat (stateful)
        """

        system_prompt = f"""
        You are a senior technical interviewer conducting a mock interview.

        JOB TITLE:
        {job_title}

        JOB DESCRIPTION:
        {job_description}

        IMPORTANT RULES:
        - DO NOT invent or assume any company name
        - If user asks for company name → say: "No company name is specified"
        - Only use the given job title and description
        - Stay strictly within the provided context
        - Ask relevant interview questions or give helpful answers
        - If information is missing → clearly say it is not specified
        - role → reply only role name (1 line)
        - job description → summarize in 2-3 lines max
        - company → always say "No company is specified"
        - avoid repeating full JD unless explicitly asked
        """

        try:
            # ✅ Build messages safely
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # ✅ Add chat history (last 10 messages only)
            if chat_history:
                messages += chat_history[-10:]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Chat reply generation failed: {str(e)}")
            return "Sorry, I could not generate a reply at this time.May be Check your internet connection"