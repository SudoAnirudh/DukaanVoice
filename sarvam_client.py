import httpx
import json
import base64
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class SarvamClient:
    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY")
        self.base_url = "https://api.sarvam.ai"
        
        # Determine headers
        self.headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }
        
    def speech_to_text(self, audio_file_path: str, language_code: str = "hi-IN") -> str:
        """
        Sends audio file to Sarvam Saaras STT API and returns transcription.
        """
        url = f"{self.base_url}/speech-to-text"
        headers = {
            "api-subscription-key": self.api_key
        }
        
        # Read file
        with open(audio_file_path, "rb") as f:
            files = {
                "file": (os.path.basename(audio_file_path), f, "audio/wav")
            }
            data = {
                "model": "saaras:v3",
                "language_code": language_code,
                "mode": "codemix"
            }
            
            try:
                response = httpx.post(url, headers=headers, files=files, data=data, timeout=30.0)
                response.raise_for_status()
                res_data = response.json()
                return res_data.get("transcript", "")
            except Exception as e:
                print(f"STT Error: {e}")
                if response := locals().get("response"):
                    print(f"STT Response Content: {response.text}")
                raise e

    def parse_command(self, transcript: str) -> Dict[str, Any]:
        """
        Queries Sarvam LLM to convert a raw transcription into structured JSON intent & entities.
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        system_instruction = (
            "You are an assistant for a Kirana store voice command system. "
            "Your job is to parse the user's transcript and extract the intent and entities as a structured JSON object. "
            "Intents can be:\n"
            "1. 'ADD_STOCK': Add/restock items to inventory (e.g. 'stock mein 10 packet maggi daalo').\n"
            "2. 'REMOVE_STOCK': Remove/sell items from inventory (e.g. 'maggi ke 2 packet kam karo').\n"
            "3. 'LOG_CREDIT': Log customer credit/udhaar (e.g. 'ramesh ko 50 rupees ki udhaar do', 'shyam ke account mein 100 rupees credit chadao').\n"
            "4. 'LOG_PAYMENT': Log customer payment received (e.g. 'ramesh ne 150 rupees diye', 'shyam ne 100 rupees pay kiye').\n"
            "5. 'UNKNOWN': Use when intent is not clear.\n\n"
            "Entities should be extracted inside an 'entities' dictionary. Clean customer_name and item_name to Title Case.\n"
            "Keys for entities:\n"
            "- For stock: 'item_name' (string), 'quantity' (integer), 'cost_price' (float, default null), 'selling_price' (float, default null)\n"
            "- For ledger: 'customer_name' (string), 'amount' (float, always positive), 'reason' (string description of goods, default null), 'phone_number' (string, default null)\n\n"
            "Return ONLY raw JSON, with no markdown formatting. Do not wrap in ```json."
        )
        
        payload = {
            "model": "sarvam-2b-instruct",  # Using a smaller fast model or fall back to sarvam-30b
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Transcript to parse: '{transcript}'"}
            ],
            "temperature": 0.0
        }
        
        try:
            # First try the smaller instruction model
            response = httpx.post(url, headers=self.headers, json=payload, timeout=20.0)
            if response.status_code == 404 or response.status_code == 400:
                # Retry with sarvam-30b
                payload["model"] = "sarvam-30b"
                response = httpx.post(url, headers=self.headers, json=payload, timeout=20.0)
            response.raise_for_status()
            
            content = response.json()["choices"][0]["message"]["content"].strip()
            # Clean possible markdown block markers
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if content.startswith("json"):
                content = content[4:].strip()
                
            return json.loads(content)
        except Exception as e:
            print(f"LLM Parsing Error: {e}")
            # Safe fallback parsing using basic regex/heuristic if LLM fails
            return self._heuristic_parse(transcript)

    def text_to_speech(self, text: str, language_code: str = "hi-IN") -> bytes:
        """
        Sends text to Sarvam Bulbul TTS API and returns the decoded audio bytes (WAV/MP3).
        """
        url = f"{self.base_url}/text-to-speech"
        
        payload = {
            "text": text,
            "target_language_code": language_code,
            "speaker": "ritu",
            "model": "bulbul:v3",
            "properties": {
                "speech_sample_rate": 24000,
                "pace": 1.05
            }
        }
        
        try:
            response = httpx.post(url, json=payload, headers=self.headers, timeout=20.0)
            response.raise_for_status()
            res_data = response.json()
            
            # Extract base64 audio and decode
            audio_b64 = res_data["audios"][0]
            return base64.b64decode(audio_b64)
        except Exception as e:
            print(f"TTS Error: {e}")
            if 'response' in locals():
                print(f"TTS Response Content: {response.text}")
            raise e

    def _heuristic_parse(self, transcript: str) -> Dict[str, Any]:
        """
        Simple keyword-based parser fallback if LLM endpoint fails.
        """
        t = transcript.lower()
        intent = "UNKNOWN"
        entities = {}
        
        # Simple parsing for stock actions
        if "stock" in t or "add" in t or "karo" in t or "packet" in t:
            intent = "ADD_STOCK"
            # Try to find quantity (numbers)
            words = t.split()
            for w in words:
                if w.isdigit():
                    entities["quantity"] = int(w)
                    break
            # Try to guess item name
            items = ["maggi", "aata", "chinni", "sugar", "rice", "oil", "biscuits"]
            for item in items:
                if item in t:
                    entities["item_name"] = item.title()
                    break
            if "item_name" not in entities:
                entities["item_name"] = "General Item"
            if "quantity" not in entities:
                entities["quantity"] = 1
                
        # Simple parsing for ledger credit
        elif "udhaar" in t or "credit" in t or "chada" in t or "likh" in t:
            intent = "LOG_CREDIT"
            words = t.split()
            for w in words:
                if w.replace(".", "", 1).isdigit():
                    entities["amount"] = float(w)
                    break
            # Guess customer
            names = ["ramesh", "suresh", "shyam", "mohan", "amit", "anil"]
            for name in names:
                if name in t:
                    entities["customer_name"] = name.title()
                    break
            if "customer_name" not in entities:
                entities["customer_name"] = "Walkin Customer"
            if "amount" not in entities:
                entities["amount"] = 50.0
                
        return {
            "intent": intent,
            "entities": entities
        }
