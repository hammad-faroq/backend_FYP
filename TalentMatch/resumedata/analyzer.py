import os
import json
import logging
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from docx import Document
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import re

# ------------------------- LOAD ENVIRONMENT VARIABLES -------------------------
load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise ValueError("❌ GROQ_API_KEY is missing. Check your .env file or environment variables.")

logger = logging.getLogger(__name__)

class EnhancedResumeAnalyzer:
    def __init__(self):
        self.client = Groq(api_key=API_KEY)
        self.models = {
            "fast": "llama-3.1-8b-instant",
            "detailed": "llama-3.1-8b-instant",
            "creative": "llama-3.1-8b-instant"
        }

    # ------------------------- TEXT EXTRACTION -------------------------
    def extract_text_from_resume(self, file_path):
        """Extract text from resume files (PDF, DOCX, DOC)"""
        ext = os.path.splitext(file_path)[1].lower()
        text = ""

        try:
            if ext == ".pdf":
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""

            elif ext in [".docx", ".doc"]:
                doc = Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])

            else:
                return f"⚠️ Unsupported file type: {ext}"

        except Exception as e:
            print(f"⚠️ Error extracting text from {ext} file: {e}")

            # PDF fallback to OCR
            if ext == ".pdf":
                try:
                    images = convert_from_path(file_path)
                    text = "\n".join(pytesseract.image_to_string(img) for img in images)
                except Exception as ocr_err:
                    print("❌ OCR failed:", ocr_err)

        return text.strip()

    # # ------------------------- COMPREHENSIVE RESUME EXTRACTION -------------------------
    # def extract_structured_resume_data(self, resume_text: str) -> Dict[str, Any]:
    #     """Extract comprehensive structured data from resume text"""
    #     if len(resume_text) > 12000:
    #         resume_text = resume_text[:12000]

    #     prompt = f"""
    #     Extract comprehensive structured data from the following resume text.
    #     Return ONLY valid JSON without any additional text.

    #     Required JSON structure:
    #     {{
    #         "personal_info": {{
    #             "full_name": "string",
    #             "email": "string",
    #             "phone": "string",
    #             "location": "string",
    #             "linkedin": "string",
    #             "github": "string",
    #             "portfolio": "string"
    #         }},
    #         "professional_summary": "string",
    #         "skills": {{
    #             "technical": ["string"],
    #             "programming_languages": ["string"],
    #             "frameworks": ["string"],
    #             "databases": ["string"],
    #             "cloud_technologies": ["string"],
    #             "devops_tools": ["string"],
    #             "soft_skills": ["string"],
    #             "languages": ["string"],
    #             "certifications_mentioned": ["string"]
    #         }},
    #         "experience": [
    #             {{
    #                 "job_title": "string",
    #                 "company": "string",
    #                 "duration": "string",
    #                 "location": "string",
    #                 "responsibilities": ["string"],
    #                 "achievements": ["string"],
    #                 "technologies_used": ["string"],
    #                 "is_current": boolean
    #             }}
    #         ],
    #         "education": [
    #             {{
    #                 "degree": "string",
    #                 "institution": "string",
    #                 "year": "string",
    #                 "grade": "string",
    #                 "field_of_study": "string",
    #                 "achievements": ["string"]
    #             }}
    #         ],
    #         "projects": [
    #             {{
    #                 "name": "string",
    #                 "description": "string",
    #                 "technologies": ["string"],
    #                 "duration": "string",
    #                 "url": "string",
    #                 "achievements": ["string"]
    #             }}
    #         ],
    #         "certifications": [
    #             {{
    #                 "name": "string",
    #                 "issuer": "string",
    #                 "date_issued": "string",
    #                 "expiry_date": "string",
    #                 "valid": boolean
    #             }}
    #         ]
    #     }}

    #     Resume Text:
    #     {resume_text}
    #     """

    #     try:
    #         response = self.client.chat.completions.create(
    #             model=self.models["detailed"],
    #             messages=[{"role": "user", "content": prompt}],
    #             temperature=0.1,
    #             max_tokens=4000,
    #             response_format={"type": "json_object"}
    #         )

    #         result = response.choices[0].message.content.strip()
    #         parsed_data = json.loads(result)
            
    #         return self._ensure_resume_structure(parsed_data)

    #     except Exception as e:
    #         logger.error(f"Error extracting structured resume data: {str(e)}")
    #         return self._get_default_resume_structure()

    # # ------------------------- CAREER PATH ANALYSIS -------------------------
    # def analyze_career_paths(self, resume_data: Dict, industry: str = "Technology") -> Dict[str, Any]:
    #     """Analyze career progression opportunities and suggest career paths"""
    #     prompt = f"""
    #     Analyze the resume data and provide comprehensive career development suggestions.
    #     Industry focus: {industry}

    #     Resume Data:
    #     {json.dumps(resume_data, indent=2)[:8000]}

    #     Provide analysis in this JSON format:
    #     {{
    #         "suitable_roles": [
    #             {{
    #                 "role": "string",
    #                 "match_score": 0-100,
    #                 "reason": "string",
    #                 "growth_potential": "high|medium|low",
    #                 "salary_range": "string",
    #                 "required_skills": ["string"],
    #                 "missing_skills": ["string"],
    #                 "timeline": "immediate|short_term|long_term"
    #             }}
    #         ],
    #         "career_trajectory": {{
    #             "current_level": "entry|mid|senior|lead|executive",
    #             "next_level": "string",
    #             "timeline_estimate": "string",
    #             "key_milestones": ["string"]
    #         }},
    #         "skill_gap_analysis": [
    #             {{
    #                 "skill": "string",
    #                 "current_level": "beginner|intermediate|advanced|expert",
    #                 "target_level": "beginner|intermediate|advanced|expert",
    #                 "importance": "critical|high|medium|low",
    #                 "learning_resources": ["string"],
    #                 "estimated_timeline": "string"
    #             }}
    #         ],
    #         "industry_insights": [
    #             {{
    #                 "trend": "string",
    #                 "impact": "positive|negative|neutral",
    #                 "recommendation": "string"
    #             }}
    #         ]
    #     }}
    #     """

    #     try:
    #         response = self.client.chat.completions.create(
    #             model=self.models["detailed"],
    #             messages=[{"role": "user", "content": prompt}],
    #             temperature=0.3,
    #             max_tokens=3000,
    #             response_format={"type": "json_object"}
    #         )

    #         result = response.choices[0].message.content.strip()
    #         return json.loads(result)

    #     except Exception as e:
    #         logger.error(f"Error analyzing career paths: {str(e)}")
    #         return {"suitable_roles": [], "skill_gap_analysis": []}

    # # ------------------------- CERTIFICATION RECOMMENDATIONS -------------------------
    # def recommend_certifications(self, resume_data: Dict, target_roles: List[str] = None) -> List[Dict]:
    #     """Recommend relevant certifications based on resume and target roles"""
    #     target_roles_text = ", ".join(target_roles) if target_roles else "Technology"

    #     prompt = f"""
    #     Based on the resume data and target roles, recommend relevant certifications for career advancement.
    #     Target roles: {target_roles_text}

    #     Resume Data:
    #     {json.dumps(resume_data, indent=2)[:6000]}

    #     Return JSON format:
    #     {{
    #         "recommended_certifications": [
    #             {{
    #                 "name": "string",
    #                 "issuer": "string (e.g., AWS, Microsoft, Google, Cisco)",
    #                 "description": "string",
    #                 "difficulty": "beginner|intermediate|advanced",
    #                 "duration": "string",
    #                 "cost": "string",
    #                 "relevance_score": 0-100,
    #                 "benefits": ["string"],
    #                 "prerequisites": ["string"],
    #                 "exam_details": "string",
    #                 "validity_period": "string",
    #                 "popularity": "high|medium|low",
    #                 "priority": "high|medium|low",
    #                 "job_market_demand": "high|medium|low"
    #             }}
    #         ]
    #     }}
    #     """

    #     try:
    #         response = self.client.chat.completions.create(
    #             model=self.models["detailed"],
    #             messages=[{"role": "user", "content": prompt}],
    #             temperature=0.2,
    #             max_tokens=3000,
    #             response_format={"type": "json_object"}
    #         )

    #         result = response.choices[0].message.content.strip()
    #         parsed = json.loads(result)
    #         return parsed.get("recommended_certifications", [])

    #     except Exception as e:
    #         logger.error(f"Error recommending certifications: {str(e)}")
    #         return []

    # ------------------------- JOB-SPECIFIC ANALYSIS -------------------------
    def analyze_resume_for_job(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        """Enhanced job matching analysis with automatic Groq, BERT, and custom model scores"""
        if len(resume_text) > 8000:
            resume_text = resume_text[:8000]

        prompt = f"""
        You are an expert AI Resume Evaluator.

        Analyze the following RESUME and JOB DESCRIPTION to determine how well the candidate matches the role.

        ### TASKS
        1. Identify **key technical and soft skills** from the resume
        2. Estimate **total years of professional experience**
        3. Detect **project or domain categories**
        4. Compare with the job description and assign a **Groq relevance rank (0–100)**
        5. Detect **CGPA**
        6. Provide **improvement suggestions**
        7. Identify **key achievements**
        8. Compute **BERT similarity score** with job description (0–100)
        9. Compute **custom ML model score** (0–100)

        Return valid JSON in this format:

        {{
        "groq_rank": <0-100>,
        "bert_similarity": <0-100>,
        "custom_model_score": <0-100>,
        "skills": ["skill1", "skill2", ...],
        "total_experience": "<number> years",
        "CGPA": "<number or 'N/A'>",
        "project_category": ["category1", "category2", ...],
        "strengths": ["string"],
        "weaknesses": ["string"],
        "improvement_suggestions": ["string"],
        "key_achievements": ["string"],
        "summary": "string"
        }}

        ### RESUME:
        {resume_text}

        ### JOB DESCRIPTION:
        {job_description}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.models["fast"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            result = response.choices[0].message.content.strip()
            parsed = json.loads(result)

            # Set defaults for missing fields
            parsed.setdefault("groq_rank", 0)
            parsed.setdefault("bert_similarity", 0)
            parsed.setdefault("custom_model_score", 0)
            parsed.setdefault("skills", [])
            parsed.setdefault("total_experience", "0")
            parsed.setdefault("CGPA", "N/A")
            parsed.setdefault("project_category", [])
            parsed.setdefault("strengths", [])
            parsed.setdefault("weaknesses", [])
            parsed.setdefault("improvement_suggestions", [])
            parsed.setdefault("key_achievements", [])
            parsed.setdefault("summary", "")

            return self.ensure_utf8(parsed)

        except Exception as e:
            logger.error(f"Error analyzing resume for job: {str(e)}")
            return {
                "groq_rank": 0,
                "bert_similarity": 0,
                "custom_model_score": 0,
                "skills": [],
                "total_experience": "0",
                "CGPA": "N/A",
                "project_category": [],
                "strengths": [],
                "weaknesses": [],
                "improvement_suggestions": [],
                "key_achievements": [],
                "summary": "Analysis failed"
            }


    # # ------------------------- LEARNING PATH RECOMMENDATIONS -------------------------
    # def generate_learning_path(self, resume_data: Dict, target_role: str) -> Dict[str, Any]:
    #     """Generate personalized learning path for career advancement"""
    #     prompt = f"""
    #     Create a personalized learning path based on the resume data and target role.

    #     Target Role: {target_role}
    #     Resume Data: {json.dumps(resume_data, indent=2)[:5000]}

    #     Return JSON format:
    #     {{
    #         "learning_path": [
    #             {{
    #                 "phase": "foundation|intermediate|advanced|specialization",
    #                 "topics": ["string"],
    #                 "resources": [
    #                     {{
    #                         "type": "course|book|tutorial|certification",
    #                         "name": "string",
    #                         "provider": "string",
    #                         "duration": "string",
    #                         "cost": "free|paid",
    #                         "url": "string"
    #                     }}
    #                 ],
    #                 "timeline": "string",
    #                 "milestones": ["string"]
    #             }}
    #         ],
    #         "estimated_timeline": "string",
    #         "key_skills_to_acquire": ["string"],
    #         "project_suggestions": [
    #             {{
    #                 "name": "string",
    #                 "description": "string",
    #                 "technologies": ["string"],
    #                 "complexity": "beginner|intermediate|advanced",
    #                 "learning_outcomes": ["string"]
    #             }}
    #         ]
    #     }}
    #     """

    #     try:
    #         response = self.client.chat.completions.create(
    #             model=self.models["creative"],
    #             messages=[{"role": "user", "content": prompt}],
    #             temperature=0.4,
    #             max_tokens=3000,
    #             response_format={"type": "json_object"}
    #         )

    #         result = response.choices[0].message.content.strip()
    #         return json.loads(result)

    #     except Exception as e:
    #         logger.error(f"Error generating learning path: {str(e)}")
    #         return {"learning_path": [], "project_suggestions": []}

    # ------------------------- COMPREHENSIVE ANALYSIS PIPELINE -------------------------
    # def comprehensive_resume_analysis(self, resume_text: str, job_description: str = None) -> Dict[str, Any]:
    #     """Complete resume analysis pipeline with all features"""
    #     try:
    #         # print(f"\n📂 Processing resume: {file_path}")
            
    #         # # Step 1: Extract text
    #         # resume_text = self.extract_text_from_resume(file_path)
    #         # if not resume_text:
    #         #     return {"error": "Resume text could not be extracted"}

    #         # # Step 2: Extract structured data
    #         # structured_data = self.extract_structured_resume_data(resume_text)

    #         # Step 3: Career path analysis
    #         career_analysis = self.analyze_career_paths(structured_data)

    #         # Step 4: Certification recommendations
    #         target_roles = [role["role"] for role in career_analysis.get("suitable_roles", [])[:3]]
    #         certifications = self.recommend_certifications(structured_data, target_roles)

    #         # Step 5: Job-specific analysis (if job description provided)
    #         job_analysis = None
    #         if job_description:
    #             job_analysis = self.analyze_resume_for_job(resume_text, job_description)

    #         # Step 6: Learning path for primary target role
    #         learning_path = None
    #         if target_roles:
    #             learning_path = self.generate_learning_path(structured_data, target_roles[0])

    #         # Compile comprehensive results
    #         result = {
    #             "success": True,
    #             "resume_summary": {
    #                 "extracted_text": resume_text,
    #                 "extracted_text_length": len(resume_text),
    #                 "primary_skills": structured_data.get("skills", {}).get("technical", [])[:10],
    #                 "experience_level": self._calculate_experience_level(structured_data),
    #                 "education_level": self._get_highest_education(structured_data)
    #             },
    #             "structured_data": structured_data,
    #             "career_analysis": career_analysis,
    #             "certification_recommendations": certifications,
    #             "job_analysis": job_analysis,
    #             "learning_path": learning_path,
    #             "analysis_timestamp": datetime.now().isoformat()
    #         }

    #         print("✅ Comprehensive Analysis Complete")
    #         return result

    #     except Exception as e:
    #         logger.error(f"Comprehensive resume analysis failed: {str(e)}")
    #         return {
    #             "success": False,
    #             "error": str(e),
    #             "analysis_timestamp": datetime.now().isoformat()
    #         }
    def comprehensive_resume_analysis(self, resume_text: str, job_description: str = None) -> Dict[str, Any]:
        try:
            if len(resume_text) > 12000:
                resume_text = resume_text[:12000]

            prompt = f"""
            You are an advanced AI Resume Analyzer.

            You MUST perform a COMPLETE and DEEP analysis of the resume.

            ⚠️ STRICT RULES (VERY IMPORTANT):
            - NEVER return incomplete lists
            - ALWAYS return at least:
                - 3 suitable roles in "suitable_roles"
                - 2 or 3 certification recommendations
                - COmplete learning path 
            - If information is missing, infer logically based on skills
            - Do NOT return fewer items even if resume is weak
            - Do NOT leave arrays empty
            - Be generous and realistic in recommendations

            Return ONLY valid JSON.

            OUTPUT FORMAT (STRICT):

            {{
                "structured_data": {{
                    "personal_info": {{
                        "full_name": "",
                        "email": "",
                        "phone": "",
                        "location": "",
                        "linkedin": "",
                        "github": "",
                        "portfolio": ""
                    }},
                    "professional_summary": "",
                    "skills": {{
                        "technical": [],
                        "programming_languages": [],
                        "frameworks": [],
                        "databases": [],
                        "cloud_technologies": [],
                        "devops_tools": [],
                        "soft_skills": [],
                        "languages": [],
                        "certifications_mentioned": []
                    }},
                    "experience": [],
                    "education": [],
                    "projects": [],
                    "certifications": []
                }},

                "career_analysis": {{
                    "suitable_roles": [
                        {{
                            "role": "",
                            "match_score": 0%,
                            "reason": "",
                            "growth_potential": "high|medium|low",
                            "salary_range": "",
                            "required_skills": [],
                            "missing_skills": [],
                            "timeline": "short_term|long_term"
                        }},
                        {{
                            "role": "",
                            "match_score": 0%,
                            "reason": "",
                            "growth_potential": "high|medium|low",
                            "salary_range": "",
                            "required_skills": [],
                            "missing_skills": [],
                            "timeline": "short_term|long_term"
                        }},
                        {{
                            "role": "",
                            "match_score": 0%,
                            "reason": "",
                            "growth_potential": "high|medium|low",
                            "salary_range": "",
                            "required_skills": [],
                            "missing_skills": [],
                            "timeline": "short_term|long_term"
                        }}
                    ]
                }},

                "certification_recommendations": [
                    {{
                        "name": "",
                        "issuer": "",
                        "description": "",
                        "difficulty": "",
                        "duration": "",
                        "cost": "",
                        "priority": "high|medium|low"
                    }},
                    {{
                        "name": "",
                        "issuer": "",
                        "description": "",
                        "difficulty": "",
                        "duration": "",
                        "cost": "",
                        "priority": "high|medium|low"
                    }},
                    {{
                        "name": "",
                        "issuer": "",
                        "description": "",
                        "difficulty": "",
                        "duration": "",
                        "cost": "",
                        "priority": "high|medium|low"
                    }},
                    {{
                        "name": "",
                        "issuer": "",
                        "description": "",
                        "difficulty": "",
                        "duration": "",
                        "cost": "",
                        "priority": "high|medium|low"
                    }},
                    {{
                        "name": "",
                        "issuer": "",
                        "description": "",
                        "difficulty": "",
                        "duration": "",
                        "cost": "",
                        "priority": "high|medium|low"
                    }}
                ],

                "learning_path": {{
                    "learning_path": [
                        {{
                            "phase": "foundation",
                            "topics": [],
                            "timeline": ""
                        }},
                        {{
                            "phase": "intermediate",
                            "topics": [],
                            "timeline": ""
                        }},
                        {{
                            "phase": "advanced",
                            "topics": [],
                            "timeline": ""
                        }},
                        {{
                            "phase": "specialization",
                            "topics": [],
                            "timeline": ""
                        }}
                    ]
                }}
            }}

            Resume:
            {resume_text}

            Job Description:
            {job_description}
            """

            response = self.client.chat.completions.create(
                model=self.models["detailed"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content.strip()
            analysis = json.loads(result)

            structured_data = analysis.get("structured_data", {})
            career_analysis = analysis.get("career_analysis", {})
            certifications = analysis.get("certification_recommendations", [])
            learning_path = analysis.get("learning_path", {})

            # Keep SAME response format (frontend safe)
            return {
                "success": True,
                "resume_summary": {
                    "extracted_text": resume_text,
                    "extracted_text_length": len(resume_text),
                    "primary_skills": structured_data.get("skills", {}).get("technical", [])[:10],
                    "experience_level": self._calculate_experience_level(structured_data),
                    "education_level": self._get_highest_education(structured_data)
                },
                "structured_data": structured_data,
                "career_analysis": career_analysis,
                "certification_recommendations": certifications,
                "learning_path": learning_path,
                "job_analysis": None,  # keep for compatibility
                "analysis_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Comprehensive resume analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis_timestamp": datetime.now().isoformat()
            }

    # ------------------------- HELPER METHODS -------------------------
    def _ensure_resume_structure(self, data: Dict) -> Dict:
        """Ensure all required fields exist in resume data"""
        structure = self._get_default_resume_structure()
        
        def merge_dicts(default, new):
            result = default.copy()
            for key, value in new.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dicts(result[key], value)
                else:
                    result[key] = value
            return result
        
        return merge_dicts(structure, data)

    def _get_default_resume_structure(self) -> Dict:
        """Default structure for resume data"""
        return {
            "personal_info": {
                "full_name": "",
                "email": "",
                "phone": "",
                "location": "",
                "linkedin": "",
                "github": "",
                "portfolio": ""
            },
            "professional_summary": "",
            "skills": {
                "technical": [],
                "programming_languages": [],
                "frameworks": [],
                "databases": [],
                "cloud_technologies": [],
                "devops_tools": [],
                "soft_skills": [],
                "languages": [],
                "certifications_mentioned": []
            },
            "experience": [],
            "education": [],
            "projects": [],
            "certifications": []
        }

    def _get_default_job_analysis(self) -> Dict:
        """Default structure for job analysis"""
        return {
            "rank": 0,
            "skills": [],
            "total_experience": "0",
            "CGPA": "N/A",
            "project_category": [],
            "strengths": [],
            "weaknesses": [],
            "improvement_suggestions": [],
            "key_achievements": [],
            "ats_optimization_score": 0,
            "recommended_keywords": []
        }

    def _calculate_experience_level(self, resume_data: Dict) -> str:
        """Calculate experience level based on work history"""
        experience = resume_data.get("experience", [])
        if len(experience) >= 8:
            return "Senior"
        elif len(experience) >= 4:
            return "Mid-level"
        elif len(experience) >= 1:
            return "Junior"
        else:
            return "Entry-level"

    def _get_highest_education(self, resume_data: Dict) -> str:
        """Get highest education level"""
        education = resume_data.get("education", [])
        if not education:
            return "Not specified"
        
        degrees = [edu.get("degree", "").lower() for edu in education]
        
        if any("phd" in deg or "doctor" in deg for deg in degrees):
            return "PhD"
        elif any("master" in deg for deg in degrees):
            return "Master's"
        elif any("bachelor" in deg or "bs" in deg or "ba" in deg for deg in degrees):
            return "Bachelor's"
        else:
            return "Diploma/Certificate"

    def ensure_utf8(self, obj):
        """Recursively ensure all strings are UTF-8 encoded."""
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="ignore")
        elif isinstance(obj, dict):
            return {k: self.ensure_utf8(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.ensure_utf8(x) for x in obj]
        elif isinstance(obj, str):
            return obj.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
        return obj

# # ------------------------- STANDALONE FUNCTIONS FOR BACKWARD COMPATIBILITY -------------------------
def extract_text_from_resume(file_path):
    """Standalone function for text extraction (used by qdrant_service)"""
    analyzer = EnhancedResumeAnalyzer()
    return analyzer.extract_text_from_resume(file_path)

def analyze_resume_with_llm(resume_text: str, job_description: str):
    """Maintain backward compatibility with existing code"""
    analyzer = EnhancedResumeAnalyzer()
    return analyzer.analyze_resume_for_job(resume_text, job_description)

def process_resume(pdf_path: str, job_description: str):
    """Maintain backward compatibility with existing code"""
    analyzer = EnhancedResumeAnalyzer()
    return analyzer.analyze_resume_for_job(
        analyzer.extract_text_from_resume(pdf_path), 
        job_description
    )