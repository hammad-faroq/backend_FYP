# cv_manager/neo4j_utils.py

import logging
import atexit
from neo4j import GraphDatabase
from django.conf import settings

logger = logging.getLogger(__name__)

# ----------------- Neo4j Driver -----------------
driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
)

# Close driver gracefully on app shutdown
atexit.register(lambda: driver.close())

# ----------------- Node & Relationship Functions -----------------
def create_user_node(tx, user_id, username):
    """Create or merge a User node"""
    tx.run(
        """
        MERGE (u:User {id: $id})
        SET u.username = $username
        """,
        id=user_id,
        username=username
    )

def create_resume_node(tx, resume_id, resume_text):
    """Create or merge a Resume node"""
    tx.run(
        """
        MERGE (r:Resume {id: $id})
        SET r.text = $text
        """,
        id=resume_id,
        text=resume_text
    )

def link_user_resume(tx, user_id, resume_id):
    """Link User -> Resume with UPLOADED relationship"""
    tx.run(
        """
        MATCH (u:User {id: $user_id}), (r:Resume {id: $resume_id})
        MERGE (u)-[:UPLOADED]->(r)
        """,
        user_id=user_id,
        resume_id=resume_id
    )

def _create_and_link_skills(tx, user_id, resume_id, skills):
    """Bulk create Skill nodes and link to both Resume and User"""
    tx.run(
        """
        UNWIND $skills AS skill_name
        MERGE (s:Skill {name: skill_name})
        WITH s
        MATCH (r:Resume {id: $resume_id}), (u:User {id: $user_id})
        MERGE (r)-[:MENTIONS]->(s)
        MERGE (u)-[:HAS_SKILL]->(s)
        """,
        skills=skills,
        resume_id=resume_id,
        user_id=user_id
    )

# ----------------- Main Function -----------------
def store_resume_in_neo4j(user_id, username, resume_id, resume_text, skills):
    """
    Store resume, user, and skills in Neo4j.
    
    Args:
        user_id: int - User primary key
        username: str - Username or email fallback
        resume_id: int - Resume primary key
        resume_text: str - Extracted resume text
        skills: list[str] - List of skill strings
    """
    try:
        # Ensure skills are clean and unique
        skills = list({skill.strip() for skill in skills if skill.strip()})

        # Use a session with default access mode (WRITE)
        with driver.session() as session:
            # 1️⃣ Create user node
            session.execute_write(create_user_node, user_id, username)

            # 2️⃣ Create resume node
            session.execute_write(create_resume_node, resume_id, resume_text)

            # 3️⃣ Link user -> resume
            session.execute_write(link_user_resume, user_id, resume_id)

            # 4️⃣ Create skills and link in bulk (if any)
            if skills:
                session.execute_write(_create_and_link_skills, user_id, resume_id, skills)

        logger.info(f"✅ Successfully stored resume {resume_id} for user {user_id} in Neo4j")

    except Exception as e:
        logger.error(f"❌ Neo4j update failed for resume {resume_id}, user {user_id}: {e}", exc_info=True)
        raise
