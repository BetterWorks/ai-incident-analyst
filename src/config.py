import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

def get_config(key, default=None, required=False):
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"Missing required config key: {key}")
    return value
