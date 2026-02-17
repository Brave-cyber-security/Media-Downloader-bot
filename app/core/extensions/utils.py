from pathlib import Path
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WORKDIR = Path(__file__).resolve().parent.parent.parent

# Remove debug print - not needed in production
logger.info(f"Working directory: {WORKDIR}")
