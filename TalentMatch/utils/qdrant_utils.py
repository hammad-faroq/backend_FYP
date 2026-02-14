#utils/qdrant_utils.py

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import os

# Connect to your local Qdrant instance (running on Docker)
# qdrant = QdrantClient(host="localhost", port=6333)


qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)



def insert_job_vector(job_id: int, vector: list[float], metadata: dict) -> None:
    """
    Insert or update a job posting embedding in Qdrant.

    Parameters
    ----------
    job_id : int
        Primary key of the JobPosting model instance.
    vector : list[float]
        768-dimensional embedding vector for the job description.
    metadata : dict
        Additional payload (e.g., {'title': 'Data Scientist', 'location': 'NY'}).
    """
    qdrant.upsert(
        collection_name="job_embeddings",
        points=[
            PointStruct(
                id=job_id,          # unique ID in Qdrant, reuse Django JobPosting id
                vector=vector,      # your 768-dimensional embedding
                payload=metadata,   # extra info stored alongside the vector
            )
        ],
    )


def search_jobs(query_vector: list[float], top_k: int = 5):
    """
    Search the Qdrant collection for the most similar job postings.

    Parameters
    ----------
    query_vector : list[float]
        768-dimensional embedding of the search text.
    top_k : int
        Number of nearest matches to return.

    Returns
    -------
    list
        A list of search results, each containing id, score, and payload.
    """
    results = qdrant.search(
        collection_name="job_embeddings",
        query_vector=query_vector,
        limit=top_k,
    )
    return results
