import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Gemini Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")

# MongoDB Config
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "compliance_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "rules")

# Pipeline Config
MAX_CHUNK_TOKENS = int(os.getenv("MAX_CHUNK_TOKENS", "12000"))
EXTRACTION_DELAY_SECONDS = int(os.getenv("EXTRACTION_DELAY_SECONDS", "2"))
MAX_REPAIR_RETRIES = int(os.getenv("MAX_REPAIR_RETRIES", "3"))
MAX_API_RETRIES = int(os.getenv("MAX_API_RETRIES", "5"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "10"))

# Validation Pipeline Config
VIOLATIONS_COLLECTION_NAME = os.getenv("VIOLATIONS_COLLECTION_NAME", "violations")
TELEMETRY_QUEUE_MAX_SIZE = int(os.getenv("TELEMETRY_QUEUE_MAX_SIZE", "1000"))
INGESTOR_HOST = os.getenv("INGESTOR_HOST", "127.0.0.1")
INGESTOR_PORT = int(os.getenv("INGESTOR_PORT", "8000"))

# Queue Config
QUEUE_TYPE = os.getenv("QUEUE_TYPE", "asyncio")
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379/0")
REDIS_QUEUE_KEY = os.getenv("REDIS_QUEUE_KEY", "swif_telemetry_queue")
