import os
import requests
import json
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
if not COHERE_API_KEY:
    raise RuntimeError("⚠️ Missing COHERE_API_KEY. Put it in your .env or export it.")

URL = "https://api.cohere.com/v2/chat"
HEADERS = {
    "Authorization": f"Bearer {COHERE_API_KEY}",
    "Content-Type": "application/json",
}

def getResponseFromPrompt(prompt: str, model: str = "command-r") -> str:
    """Send a simple chat prompt to Cohere and return text response."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post(URL, headers=HEADERS, json=payload, timeout=45)
    r.raise_for_status()
    data = r.json()

    # Cohere v2/chat may return "text" OR structured content
    if "text" in data:
        return data["text"].strip()
    if "message" in data and "content" in data["message"]:
        parts = data["message"]["content"]
        if parts and isinstance(parts, list):
            return parts[0].get("text", "").strip()
    return json.dumps(data, indent=2)


# if __name__ == "__main__":
#     prompt = """Generate 3 French vocabulary flashcards.
# Each line should be formatted as:
# Q: <word> | A: <translation>"""

#     response = getResponseFromPrompt(prompt)
#     print("=== Raw Cohere output ===")
#     print(response)