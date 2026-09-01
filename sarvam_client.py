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
        
    async def speech_to_text(self, audio_file_path: str, language_code: str = "unknown") -> tuple[str, str]:
        """
        Sends audio file to Sarvam Saaras STT API asynchronously and returns a tuple of (transcription, language_code).
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
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, headers=headers, files=files, data=data)
                    response.raise_for_status()
                    res_data = response.json()
                    transcript = res_data.get("transcript", "")
                    detected_lang = res_data.get("language_code") or language_code
                    if detected_lang == "unknown":
                        detected_lang = "hi-IN"
                    return transcript, detected_lang
            except Exception as e:
                print(f"STT Error: {e}")
                if response := locals().get("response"):
                    print(f"STT Response Content: {response.text}")
                raise e

    async def parse_command(self, transcript: str, detected_lang: str = "hi-IN") -> Dict[str, Any]:
        """
        Queries Sarvam LLM asynchronously to convert a raw transcription into structured JSON intent & entities,
        including a voice confirmation sentence in the user's spoken language.
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
            "5. 'QUERY_STOCK': Query current stock quantity of an item (e.g. 'maggi ka kitna stock hai?', 'kitne packet aata bacha hai?').\n"
            "6. 'QUERY_BALANCE': Query outstanding credit balance of a customer (e.g. 'ramesh ka kitna udhaar baaki hai?', 'shyam ka balance batao').\n"
            "7. 'UNKNOWN': Use when intent is not clear.\n\n"
            "Entities should be extracted inside an 'entities' dictionary. Clean customer_name and item_name to Title Case.\n"
            "Keys for entities:\n"
            "- For stock add/remove/query: 'item_name' (string), 'quantity' (integer, default 1 for mutation), 'cost_price' (float, default null), 'selling_price' (float, default null)\n"
            "- For ledger credit/payment/query: 'customer_name' (string), 'amount' (float, default 0), 'reason' (string description of goods, default null), 'phone_number' (string, default null)\n\n"
            f"Additionally, you MUST generate a short, natural confirmation message in the user's detected language: {detected_lang}. "
            "For example, if query is QUERY_STOCK for Maggi, write a sentence stating that you are checking Maggi stock. "
            "Return this message under the 'confirmation_message' key in the JSON object.\n\n"
            "Return ONLY raw JSON, with no markdown formatting. Do not wrap in ```json."
        )
        
        payload = {
            "model": "sarvam-30b",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"Transcript to parse: '{transcript}'"}
            ],
            "temperature": 0.0
        }
        
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, headers=self.headers, json=payload)
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
            res = self._heuristic_parse(transcript)
            res["confirmation_message"] = "Action processed."
            return res

    async def text_to_speech(self, text: str, language_code: str = "hi-IN") -> bytes:
        """
        Sends text to Sarvam Bulbul TTS API asynchronously and returns the decoded audio bytes (WAV/MP3).
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
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
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
        
        # Check query balance
        if "kitna udhaar" in t or "kitna balance" in t or "udhaar kitna" in t:
            intent = "QUERY_BALANCE"
            names = ["ramesh", "suresh", "shyam", "mohan", "amit", "anil"]
            for name in names:
                if name in t:
                    entities["customer_name"] = name.title()
                    break
            if "customer_name" not in entities:
                entities["customer_name"] = "Ramesh Kumar"

        # Check query stock
        elif "kitna stock" in t or "kitna bacha" in t or "stock kitna" in t:
            intent = "QUERY_STOCK"
            items = ["maggi", "aata", "chinni", "sugar", "rice", "oil", "biscuits"]
            for item in items:
                if item in t:
                    entities["item_name"] = item.title()
                    break
            if "item_name" not in entities:
                entities["item_name"] = "Maggi Noodles"

        # Simple parsing for stock actions
        elif "stock" in t or "add" in t or "karo" in t or "packet" in t:
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

