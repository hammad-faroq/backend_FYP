import os
import docx2txt
import PyPDF2
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from difflib import SequenceMatcher
from jobs.models import Job
from django.conf import settings

# ✅ Use Qdrant Cloud settings from env
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "final_job_embeddings"
RESUME_COLLECTION = "final_resume"

# ✅ Initialize Qdrant cloud client
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# ✅ Initialize BERT model
bert_model = SentenceTransformer("all-MiniLM-L6-v2")
# qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# ------------------------- RESUME TEXT EXTRACTION -------------------------
def extract_text_from_resume(file_path):
    """Extract text from resume files - standalone function"""
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

# ------------------------- SYNC JOBS TO QDRANT -------------------------
def sync_job_descriptions():
    """Push all job descriptions from DB into Qdrant."""
    print("🔄 Syncing job descriptions to Qdrant...")

    # ✅ Recreate or ensure collection exists
    try:
        qdrant.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(size=384, distance=qmodels.Distance.COSINE),
        )
    except Exception as e:
        print(f"⚠️ Collection creation issue: {e}")

    # ✅ Fetch jobs from Job model
    jobs = Job.objects.all()
    if not jobs.exists():
        print("⚠️ No Job records found.")
        return

    # ✅ Convert job descriptions to embeddings
    job_descriptions = [job.description for job in jobs if job.description]
    if not job_descriptions:
        print("⚠️ No job descriptions found.")
        return

    vectors = bert_model.encode(job_descriptions)

    # ✅ Prepare Qdrant points
    points = []
    for i, (job, vec) in enumerate(zip(jobs, vectors)):
        if job.description:  # Only include jobs with descriptions
            points.append(
                qmodels.PointStruct(
                    id=job.id or i + 1,  # Ensure unique ID
                    vector=vec.tolist(),
                    payload={
                        "title": job.title or "",
                        "description": job.description or "",
                        "requirements": getattr(job, 'requirements', '') or "",
                    },
                )
            )

    # ✅ Upload to Qdrant
    if points:
        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"✅ {len(points)} job descriptions synced to Qdrant.")
    else:
        print("⚠️ No points to sync.")

# ------------------------- RESUME ANALYSIS -------------------------
def process_resume(resume_path, job_description_text=None, job_id=None):
    """Compare resume embedding only against the specific job embedding"""
    resume_text = extract_text_from_resume(resume_path)
    if not resume_text or resume_text.startswith("[Error"):
        return {"similarity_score": 0, "summary": "Could not read resume text."}

    if not job_id:
        return {"similarity_score": 0, "summary": "Job ID required for relevant job comparison."}

    # --- Retrieve job vector safely ---
    try:
        job_point = qdrant.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[job_id],
            with_vectors=True
        )

        if not job_point or not job_point[0].vector:
            return {
                "similarity_score": 0,
                "summary": f"No embedding vector found for job ID {job_id}. Try re-syncing."
            }

        job_vector = job_point[0].vector

    except Exception as e:
        return {"similarity_score": 0, "summary": f"Error retrieving job vector: {e}"}

    # --- Encode resume and compute similarity ---
    from numpy import dot
    from numpy.linalg import norm
    resume_vector = bert_model.encode(resume_text).tolist()

    try:
        similarity = dot(job_vector, resume_vector) / (norm(job_vector) * norm(resume_vector))
        similarity_percentage = round(float(similarity) * 100, 2)
    except Exception as e:
        return {"similarity_score": 0, "summary": f"Error computing similarity: {e}"}

    return {
        "similarity_score": similarity_percentage,
        "summary": f"Resume matches this job by {similarity_percentage}% similarity."
    }

# ----------------- RESUME VECTOR STORAGE -----------------
def add_resume_to_qdrant(user_id, resume_text, resume_data=None):
    """
    Extract text, embed, and store resume vector in Qdrant.
    """
    print(f"📄 Adding resume for user {user_id}...")

    if not resume_text:
        print(f"⚠️ No text provided for user {user_id}")
        return

    # Ensure collection exists
    try:
        qdrant.get_collection(RESUME_COLLECTION)
    except Exception:
        qdrant.recreate_collection(
            collection_name=RESUME_COLLECTION,
            vectors_config=qmodels.VectorParams(size=384, distance=qmodels.Distance.COSINE),
        )
        print(f"✅ Created collection '{RESUME_COLLECTION}'")

    # Encode resume text
    vector = bert_model.encode(resume_text).tolist()

    # Prepare payload
    payload = {
        "user_id": user_id,
        "text": resume_text[:1000],  # Store first 1000 chars
    }
    
    # Add structured data if available
    if resume_data:
        payload["structured_data"] = resume_data

    # Store in Qdrant
    qdrant.upsert(
        collection_name=RESUME_COLLECTION,
        points=[
            qmodels.PointStruct(
                id=user_id,  # Use user_id as point ID
                vector=vector,
                payload=payload,
            )
        ],
    )

    print(f"✅ Stored resume vector for user {user_id} in Qdrant.")

# ----------------- SEARCH SIMILAR RESUMES -----------------
def search_similar_resumes(query_text, top_k=5):
    """
    Given a text query (like a job description),
    returns the top K most similar resumes.
    """
    vector = bert_model.encode(query_text).tolist()

    try:
        results = qdrant.search(
            collection_name=RESUME_COLLECTION,
            query_vector=vector,
            limit=top_k,
        )

        return [
            {
                "user_id": hit.payload.get("user_id"),
                "score": hit.score,
                "text_snippet": hit.payload.get("text", "")[:300],
            }
            for hit in results
        ]
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return []