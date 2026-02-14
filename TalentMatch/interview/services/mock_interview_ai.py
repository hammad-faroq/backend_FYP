import os
import json
import logging
from groq import Groq
from dotenv import load_dotenv
import time

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY missing")


class MockInterviewAI:
    """
    Handles mock interview generation, sanitization, and evaluation.
    """

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = "llama-3.1-8b-instant"

    # ----------------------------------
    # Generate interview questions
    # ----------------------------------
    def generate_questions(
        self,
        job_title: str,
        job_description: str,
        difficulty: str = "medium",
        interview_type: str = "technical",
        total_questions: int = 10,
        retries: int = 3
    ) -> list:
        """Generate interview questions via AI and return a list of dicts."""

        prompt = f"""
Create EXACTLY {total_questions} {difficulty} {interview_type} interview questions.

JOB TITLE:
{job_title}

JOB DESCRIPTION:
{job_description}

RULES:
- Each item MUST contain:
  - question
  - ideal_answer
- NO explanations or extra text

RETURN STRICT JSON ARRAY
"""

        for attempt in range(1, retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000
                )

                raw_content = response.choices[0].message.content.strip()

                # Remove code fences if present
                if raw_content.startswith("```"):
                    raw_content = raw_content.split("\n", 1)[-1]
                    raw_content = raw_content.rsplit("```", 1)[0].strip()

                if not raw_content:
                    logger.warning(f"Attempt {attempt}: AI returned empty content")
                    continue

                try:
                    questions = json.loads(raw_content)
                    if not isinstance(questions, list):
                        logger.warning(f"Attempt {attempt}: Expected list, got {type(questions)}")
                        continue

                    # 🔹 Ensure exactly total_questions
                    if len(questions) < total_questions:
                        logger.warning(f"AI returned {len(questions)} questions, padding to {total_questions}")
                        while len(questions) < total_questions:
                            questions.append(questions[-1].copy())
                    elif len(questions) > total_questions:
                        questions = questions[:total_questions]

                    return questions

                except json.JSONDecodeError:
                    logger.warning(f"Attempt {attempt}: JSON decode error: {raw_content}")
                    continue

            except Exception as e:
                logger.warning(f"Attempt {attempt}: AI generation failed: {str(e)}")
                time.sleep(1)  # small delay before retry

        logger.error("Failed to generate questions after multiple attempts")
        return []

    # ----------------------------------
    # Sanitize question for candidate
    # ----------------------------------
    def sanitize_question(self, question: dict) -> dict:
        """Remove ideal_answer before sending to candidate."""
        return {"question": question.get("question") or question.get("scenario")}

    # ----------------------------------
    # Evaluate candidate answer
    # ----------------------------------
    def evaluate_answer(
        self,
        job_title: str,
        job_description: str,
        question: dict,
        candidate_answer: str
    ) -> dict:
        """Evaluate candidate's answer against ideal answer."""

        prompt = f"""
You are a senior interviewer.

QUESTION:
{question['question']}

IDEAL ANSWER:
{question['ideal_answer']}

CANDIDATE ANSWER:
{candidate_answer}

TASK:
Return STRICT JSON:
{{
  "score": number (0-10),
  "feedback": "string",
  "improvement_tips": ["string"]
}}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            raw_content = response.choices[0].message.content.strip()
            if isinstance(raw_content, str):
                return json.loads(raw_content)
            return raw_content

        except Exception as e:
            logger.error(f"AI evaluation failed: {str(e)}")
            return {
                "score": 0,
                "feedback": "Evaluation failed",
                "improvement_tips": []
            }