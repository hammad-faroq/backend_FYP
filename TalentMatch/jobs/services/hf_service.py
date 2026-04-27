import time
import logging
import json
import requests

logger = logging.getLogger(__name__)

HF_SPACE_NAME = "Irfaniiioo/cvjdgradio"

def wake_up_space():
    try:
        requests.get("https://irfaniiioo-cvjdgradio.hf.space", timeout=30)
        time.sleep(5)  # wait for it to wake up
    except:
        pass

def normalize_hf_result(hf_data: dict) -> dict:
    """Normalize the HF API response to a consistent format."""
    
    # Fix score — API returns 'Total_score' not 'score'
    score = hf_data.get("Total_score", hf_data.get("score", 0)) or 0

    # Fix matching_analysis — API returns a list, convert to bullet string
    matching = hf_data.get("matching_analysis", "")
    if isinstance(matching, list):
        matching = "\n• " + "\n• ".join(matching)

    return {
        "matching_analysis": matching,
        "description": hf_data.get("description", ""),
        "score": score,
        "recommendation": hf_data.get("recommendation", ""),
        "name": hf_data.get("name", ""),
        "email": hf_data.get("email_adress", ""),   # note: typo is in their API
        "phone": hf_data.get("phone_number", ""),
    }


def call_hf_model_with_retry(resume_text: str, job_description: str, max_retries=3, delay=15):
    wake_up_space()
    for attempt in range(max_retries):
        try:
            logger.info(f"HF API call attempt {attempt + 1}/{max_retries}")

            try:
                from gradio_client import Client
            except ImportError:
                logger.error("gradio_client not installed. Run: pip install gradio_client")
                return {
                    "success": False,
                    "data": normalize_hf_result({}),
                    "score": 0,
                    "error": "gradio_client not installed"
                }

            client = Client(HF_SPACE_NAME)
            result = client.predict(
                cv=resume_text,
                job_description=job_description,
                api_name="/match_cv_job"
            )
            print(result)

            logger.info(f"HF API raw result: {result}")

            if result and isinstance(result, (dict, str)):
                # Parse string to dict if needed
                if isinstance(result, str):
                    try:
                        hf_data = json.loads(result)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse result as JSON: {result}")
                        hf_data = {"matching_analysis": result, "description": "Raw response"}
                else:
                    hf_data = result

                # ✅ Normalize here
                normalized = normalize_hf_result(hf_data)
                logger.info(f"HF API normalized: {normalized}")

                return {
                    "success": True,
                    "data": normalized,
                    "score": normalized["score"]    # always correct now
                }
            else:
                logger.warning(f"HF API returned unexpected format: {result}")

        except Exception as e:
            logger.error(f"HF API error on attempt {attempt + 1}: {str(e)}")
            if "Connection" in str(e) or "timeout" in str(e).lower():
                logger.warning("Space might be sleeping or unavailable")

        if attempt < max_retries - 1:
            logger.info(f"Waiting {delay} seconds before retry...")
            time.sleep(delay)

    logger.error(f"HF API failed after {max_retries} attempts")
    return {
        "success": False,
        "data": {
            "matching_analysis": "Analysis unavailable after multiple attempts",
            "description": "The HuggingFace Gradio space is currently unavailable or sleeping.",
            "score": 0,
            "recommendation": "The space may need to wake up. Try again in a few minutes.",
            "name": "", "email": "", "phone": "",
            "error": True
        },
        "score": 0,
        "error": "Max retries exceeded"
    }