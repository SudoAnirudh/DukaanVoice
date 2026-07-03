import os
import httpx
from dotenv import load_dotenv

load_dotenv()

def test_llm():
    api_key = os.getenv("SARVAM_API_KEY")
    url = "https://api.sarvam.ai/v1/chat/completions"
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sarvam-30b",
        "messages": [
            {"role": "user", "content": "Say 'API is authorized and working successfully!' in one short sentence."}
        ],
        "temperature": 0.0
    }
    print("[*] Testing LLM endpoint...")
    response = httpx.post(url, headers=headers, json=payload)
    print(f"[LLM] Status: {response.status_code}")
    print(f"[LLM] Response: {response.text}")

def test_tts():
    api_key = os.getenv("SARVAM_API_KEY")
    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": "Aaj ki kul sales do sau rupaye hai.",
        "target_language_code": "hi-IN",
        "speaker": "ritu",
        "model": "bulbul:v3",
        "properties": {
            "speech_sample_rate": 24000,
            "pace": 1.05
        }
    }
    print("[*] Testing TTS endpoint...")
    response = httpx.post(url, headers=headers, json=payload)
    print(f"[TTS] Status: {response.status_code}")
    print(f"[TTS] Response: {response.text}")

if __name__ == "__main__":
    test_llm()
    test_tts()
