import os
import docx2txt
import PyPDF2
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from jobs.models import Job
from django.conf import settings

COLLECTION_NAME = "JOBS"

# lazy globals
_bert_model = None
_qdrant = None

def get_bert_model():
    global _bert_model
    if _bert_model is None:
        _bert_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _bert_model

def get_qdrant():
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY
        )
    return _qdrant

# ------------------------- RESUME TEXT EXTRACTION -------------------------
def extract_text_from_resume(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    try:
        if ext == ".pdf":
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
        elif ext == ".docx":
            text = docx2txt.process(file_path)
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            text = "[Unsupported file format]"
    except Exception as e:
        text = f"[Error reading file: {e}]"
    return text.strip()

def ensure_collection_exists():
    qdrant = get_qdrant()
    collections = qdrant.get_collections().collections
    names = [c.name for c in collections]
    if COLLECTION_NAME not in names:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(size=384, distance=qmodels.Distance.COSINE)
        )
        print("✅ JOBS collection created")
    else:
        print("ℹ️ JOBS collection already exists")

# ------------------------- SYNC JOBS TO QDRANT -------------------------
def sync_job_descriptions():
    print("🔄 Syncing job descriptions to Qdrant...")
    qdrant = get_qdrant()
    bert_model = get_bert_model()
    ensure_collection_exists()

    jobs = Job.objects.all()
    if not jobs.exists():
        print("⚠️ No Job records found.")
        return

    texts = []
    valid_jobs = []
    for job in jobs:
        if job.description:
            text = f"""
            Title: {job.title}
            Company: {job.company_name}
            Location: {job.location}
            Description: {job.description}
            Requirements: {job.requirements}
            """
            texts.append(text)
            valid_jobs.append(job)

    vectors = bert_model.encode(texts)
    points = []
    for job, vec in zip(valid_jobs, vectors):
        points.append(
            qmodels.PointStruct(
                id=job.id,
                vector=vec.tolist(),
                payload={
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company_name,
                    "location": job.location,
                }
            )
        )

    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"✅ {len(points)} jobs synced safely.")

# ------------------------- RESUME ANALYSIS -------------------------
def process_resume(resume_path):
    qdrant = get_qdrant()
    bert_model = get_bert_model()
    
    resume_text = extract_text_from_resume(resume_path)
    if not resume_text:
        return {"similarity_score": 0, "summary": "Could not read resume"}

    resume_vector = bert_model.encode(resume_text).tolist()
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=resume_vector,
        limit=5,
        with_payload=True
    )

    matches = []
    for r in results:
        matches.append({
            "job_id": r.payload.get("job_id"),
            "title": r.payload.get("title"),
            "company": r.payload.get("company"),
            "score": round(float(r.score), 4)
        })

    return {
        "similarity_score": matches[0]["score"] if matches else 0,
        "matches": matches
    }