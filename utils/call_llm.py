import os
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
import requests

# Load environment variables from .env
load_dotenv()

# Configure logging
log_directory = os.getenv("LOG_DIR", "logs")
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(
    log_directory, f"llm_calls_{datetime.now().strftime('%Y%m%d')}.log"
)

# Set up logger
logger = logging.getLogger("llm_logger")
logger.setLevel(logging.INFO)
logger.propagate = False
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)

# Cache file
cache_file = "llm_cache.json"

# Function to call LLaMA via Ollama
def call_llm(prompt: str, use_cache: bool = True) -> str:
    logger.info(f"PROMPT: {prompt}")

    # Load from cache if enabled
    cache = {}
    if use_cache and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            logger.warning("Failed to load cache, starting with empty cache")

        if prompt in cache:
            logger.info(f"RESPONSE (from cache): {cache[prompt]}")
            return cache[prompt]

    # Read model name from environment or use default
    model = os.getenv("LLM_MODEL", "llama3")  # Make sure llama3 is pulled in Ollama

    # Send prompt to Ollama
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
    except Exception as e:
        logger.error(f"Failed to connect to Ollama server: {e}")
        raise Exception(f"Ollama connection error: {e}")

    if response.status_code != 200:
        error_msg = f"Ollama API call failed: {response.status_code}: {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)

    try:
        response_text = response.json().get("response", "").strip()
    except Exception as e:
        logger.error(f"Failed to parse Ollama response: {e}")
        raise Exception(f"Parsing error: {e}")

    logger.info(f"RESPONSE: {response_text}")

    # Save to cache
    if use_cache:
        cache[prompt] = response_text
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

    return response_text

# Example test
if __name__ == "__main__":
    test_prompt = "Hi."
    print("Making call...")
    response = call_llm(test_prompt, use_cache=False)
    print(f"Response: {response}")
