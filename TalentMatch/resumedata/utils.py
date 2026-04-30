import os
import joblib  # or pickle
from django.conf import settings

# Load once at startup
MODEL_PATH = getattr(settings, "MY_MODEL_PATH", None)

if not MODEL_PATH or not os.path.exists(MODEL_PATH):
    raise ValueError(f"❌ Custom model file not found at {MODEL_PATH}")

print(f"📂 Loading custom ML model from {MODEL_PATH}...")
custom_model = joblib.load(MODEL_PATH)
