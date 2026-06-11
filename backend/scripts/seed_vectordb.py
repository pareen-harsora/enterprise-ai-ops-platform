import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_store import seed_vector_store
from app.core.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Seeding ChromaDB Vector Store")
    logger.info("=" * 50)
    count = seed_vector_store()
    logger.info(f"Successfully seeded {count} document chunks")
    logger.info("=" * 50)