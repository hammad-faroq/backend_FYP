import os
import joblib
from django.conf import settings

_custom_model = None

def get_custom_model():
    global _custom_model
    if _custom_model is None:
        MODEL_PATH = getattr(settings, "MY_MODEL_PATH", None)
        if not MODEL_PATH or not os.path.exists(MODEL_PATH):
            raise ValueError(f"❌ Custom model file not found at {MODEL_PATH}")
        print(f"📂 Loading custom ML model from {MODEL_PATH}...")
        _custom_model = joblib.load(MODEL_PATH)
    return _custom_model