import logging
import sys

# Define logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Silence third-party logs slightly for clarity
    logging.getLogger("pydantic").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("celery").setLevel(logging.INFO)

# Run setup
setup_logging()
logger = logging.getLogger("cinerec-backend")
