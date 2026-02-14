import requests
import json
import os
from dotenv import load_dotenv
# ✅ Use a model trained for resume NER / structured extraction
HUGGINGFACE_API_URL =os.environ.get('HUGGINGFACE_API_URL') 
HUGGINGFACE_TOKEN = os.environ.get('HUGGINGFACE_TOKEN') 

def is_resume(text):
    headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
    prompt = f"""
    This is a document:
    {text}

    Determine whether it is a professional resume.
    Respond only with 'resume' or 'not a resume'.
    """
    payload = {"inputs": prompt}

    try:
        response = requests.post(HUGGINGFACE_API_URL, headers=headers, json=payload, timeout=30)
        result = response.json()

        # Handle list or dict
        if isinstance(result, list) and len(result) > 0:
            label = result[0].get("generated_text", "").lower()
        elif isinstance(result, dict):
            label = result.get("generated_text", "").lower()
        else:
            label = ""

        return "resume" in label

    except Exception as e:
        print(f"⚠️ Resume check failed: {e}")
        return False


def call_llm_structured_resume(text):
    """
    Extract structured resume information from raw text.
    Returns a JSON dict with all keys; missing fields set to None.
    """
    headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
    prompt = f"""
    This is the raw text of a resume:

    {text}

    Extract the following information as a valid JSON object with keys:
    full_name, email, phone, linkedin, github, summary,
    education (list), experience (list), skills (list),
    projects (list), certifications (list), interests (list).

    If a field is missing, set its value to null. Only return JSON.
    """

    payload = {"inputs": prompt}

    try:
        response = requests.post(HUGGINGFACE_API_URL, headers=headers, json=payload, timeout=60)
        result = response.json()

        # The model returns 'generated_text'
        generated_text = result.get("generated_text", "{}").strip()
        if not generated_text:
            generated_text = "{}"

    except Exception as e:
        print(f"⚠️ LLM request failed: {e}")
        generated_text = "{}"

    # Convert to JSON safely
    try:
        structured_json = json.loads(generated_text)
    except Exception as e:
        print(f"⚠️ Failed to parse LLM output as JSON: {e}")
        structured_json = {}

    # Ensure all keys exist; missing or empty fields set to None
    keys = [
        "full_name", "email", "phone", "linkedin", "github", "summary",
        "education", "experience", "skills", "projects", "certifications", "interests"
    ]
    for key in keys:
        if key not in structured_json or structured_json[key] in ["", [], None]:
            structured_json[key] = None

    return structured_json
