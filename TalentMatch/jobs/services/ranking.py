# jobs/services/ranking.py

def calculate_rank(
    groq_rank: float,
    bert_similarity: float,
    custom_model_score: float,
    weights=None
):
    """
    Centralized resume ranking logic.
    All scores expected in range 0–100.
    Returns a combined rank score (0–100).
    """

    # Default weights if none provided
    if not weights:
        weights = {
            "groq": 0.4,     # LLM semantic relevance
            "bert": 0.3,     # Vector similarity
            "custom": 0.3,   # ML model score
        }

    try:
        groq_rank = float(groq_rank or 0)
        bert_similarity = float(bert_similarity or 0)
        custom_model_score = float(custom_model_score or 0)

        # Normalize weights to sum to 1
        total_weight = sum(weights.values())
        if total_weight == 0:
            total_weight = 1
        norm_weights = {k: v / total_weight for k, v in weights.items()}

        combined_score = (
            (groq_rank * norm_weights["groq"]) +
            (bert_similarity * norm_weights["bert"]) +
            (custom_model_score * norm_weights["custom"])
        )

        # Ensure the score is within 0–100
        combined_score = max(0, min(100, combined_score))

        return round(combined_score, 2)

    except Exception as e:
        print("❌ Rank calculation failed:", e)
        return 0.0
