import os
import uuid
import urllib.parse
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
import csv

from database import (
    init_db, get_inventory, update_inventory_stock,
    get_ledger, add_ledger_entry, get_daily_summary,
    get_outstanding_reminders
)
from sarvam_client import SarvamClient

# Initialize FastAPI
app = FastAPI(title="DukaanVoice API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Client
sarvam_client = SarvamClient()

# Static Directories Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
AUDIO_CACHE_DIR = os.path.join(STATIC_DIR, "audio_cache")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

# PIN gate request model
class PINRequest(BaseModel):
    pin: str

# Initialize DB on Startup
@app.on_event("startup")
def startup_event():
    init_db()
    # Create a default system error audio file if it doesn't exist
    error_audio_file = os.path.join(AUDIO_CACHE_DIR, "error.wav")
    if not os.path.exists(error_audio_file):
        try:
            # Generate a default voice warning for errors
            err_bytes = sarvam_client.text_to_speech("Samajh nahi aaya, kripya dobara bole.")
            with open(error_audio_file, "wb") as f:
                f.write(err_bytes)
        except Exception:
            # Write a 1-byte placeholder if offline/API fails
            with open(error_audio_file, "wb") as f:
                f.write(b"")

# --- PIN Lock Gate ---
@app.post("/api/verify-pin")
def verify_pin(req: PINRequest):
    env_pin = os.getenv("SHOP_PIN", "1234")
    if req.pin == env_pin:
        return {"status": "success", "authenticated": True}
    raise HTTPException(status_code=401, detail="Incorrect shop PIN code.")

# --- Read Operations ---
@app.get("/api/inventory")
def api_get_inventory():
    return get_inventory()

@app.get("/api/ledger")
def api_get_ledger():
    return get_ledger()

# --- Voice Command Transaction Process ---
@app.post("/api/voice-command")
async def voice_command(audio_file: UploadFile = File(...)):
    # 1. Save uploaded file temporarily
    temp_filename = f"temp_{uuid.uuid4().hex}.wav"
    temp_filepath = os.path.join(AUDIO_CACHE_DIR, temp_filename)
    
    try:
        with open(temp_filepath, "wb") as buffer:
            buffer.write(await audio_file.read())
            
        # 2. Convert Speech-to-Text using Sarvam Saaras (auto-detect language)
        transcript, detected_lang = sarvam_client.speech_to_text(temp_filepath, language_code="unknown")
        if not transcript:
            raise HTTPException(status_code=400, detail="Microphone audio could not be transcribed.")
            
        # 3. Parse intent and entities using LLM
        parsed = sarvam_client.parse_command(transcript, detected_lang=detected_lang)
        intent = parsed.get("intent", "UNKNOWN")
        entities = parsed.get("entities", {})
        confirmation_message = parsed.get("confirmation_message")
        
        # 4. Process DB Action
        db_updated = False
        message = ""
        low_stock_warnings = []
        
        if intent == "ADD_STOCK":
            item = entities.get("item_name", "General Item")
            qty = entities.get("quantity", 1)
            cost = entities.get("cost_price")
            sell = entities.get("selling_price")
            
            updated = update_inventory_stock(item, qty, cost, sell)
            db_updated = True
            message = f"{qty} packet {item} stock mein add kar diye gaye hain."
            
        elif intent == "REMOVE_STOCK":
            item = entities.get("item_name", "General Item")
            qty = entities.get("quantity", 1)
            
            updated = update_inventory_stock(item, -qty)
            db_updated = True
            message = f"{qty} packet {item} stock se kam kar diye gaye hain."
            
            # Check for low stock threshold
            current_qty = updated.get("quantity", 0)
            threshold = updated.get("low_stock_threshold", 3)
            if current_qty <= threshold:
                low_stock_warnings.append(f"{item} sirf {current_qty} packet bache hain.")
                
        elif intent == "LOG_CREDIT":
            customer = entities.get("customer_name", "Walkin")
            amount = entities.get("amount", 0.0)
            reason = entities.get("reason", "Goods")
            phone = entities.get("phone_number")
            
            add_ledger_entry(customer, amount, reason, phone)
            db_updated = True
            message = f"{customer} ke khate mein {amount} rupaye udhaar likh diye gaye hain."
            
        elif intent == "LOG_PAYMENT":
            customer = entities.get("customer_name", "Walkin")
            amount = entities.get("amount", 0.0)
            phone = entities.get("phone_number")
            
            add_ledger_entry(customer, -amount, "Payment Received", phone)
            db_updated = True
            message = f"{customer} ne {amount} rupaye jama kiye hain."
            
        else:
            message = "Command samajh nahi aaya. Kripya dobara koshish karein."
            
        # Use LLM-generated confirmation message if available, fallback to Hindi templates
        tts_prompt = confirmation_message or message
        
        # Match language code to supported Bulbul v3 list
        supported_langs = ["hi-IN", "bn-IN", "ta-IN", "te-IN", "gu-IN", "kn-IN", "ml-IN", "mr-IN", "pa-IN", "od-IN", "en-IN"]
        tts_lang = detected_lang if detected_lang in supported_langs else "hi-IN"
        
        # Append stock alert to audio prompt if triggered
        if low_stock_warnings:
            if tts_lang.startswith("hi"):
                tts_prompt += " Warning! " + " aur ".join(low_stock_warnings)
            else:
                tts_prompt += " Warning! Low stock for " + " and ".join(low_stock_warnings)
            
        # 5. Synthesize TTS response via Bulbul v3 in the detected language
        tts_filename = f"confirm_{uuid.uuid4().hex}.wav"
        tts_filepath = os.path.join(AUDIO_CACHE_DIR, tts_filename)
        
        try:
            audio_bytes = sarvam_client.text_to_speech(tts_prompt, language_code=tts_lang)
            with open(tts_filepath, "wb") as f:
                f.write(audio_bytes)
            tts_audio_url = f"/static/audio_cache/{tts_filename}"
        except Exception as tts_err:
            print(f"TTS Synthesis Failed: {tts_err}")
            # Fallback to general success response sound
            tts_audio_url = "/static/audio_cache/error.wav"
            
        return {
            "status": "success",
            "transcription": transcript,
            "parsed_command": parsed,
            "database_updated": db_updated,
            "tts_audio_url": tts_audio_url,
            "message": tts_prompt
        }
        
    except Exception as e:
        print(f"Voice Command Pipeline Error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "tts_audio_url": "/static/audio_cache/error.wav"
        }
    finally:
        # Clean up temp file
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

# --- Daily Summary EOD ---
@app.get("/api/daily-summary")
def api_daily_summary():
    summary = get_daily_summary()
    
    total_sales = summary.get("total_sales", 0.0)
    total_credit = summary.get("total_credit_given", 0.0)
    top_items = summary.get("top_items", [])
    
    # Construct EOD summary speech
    spoken_text = f"Aaj ki kul cash bikri {total_sales} rupaye rahi. Aur kul {total_credit} rupaye ka credit yaani udhaar diya gaya."
    
    if top_items:
        items_desc = []
        for item in top_items:
            items_desc.append(f"{item['item_name']} jiske {item['quantity_sold']} transaction hue")
        spoken_text += " Aaj ke top items hain: " + ", ".join(items_desc)
    else:
        spoken_text += " Aaj koi specific item transaction nahi hua."
        
    tts_filename = f"summary_{uuid.uuid4().hex}.wav"
    tts_filepath = os.path.join(AUDIO_CACHE_DIR, tts_filename)
    
    try:
        audio_bytes = sarvam_client.text_to_speech(spoken_text)
        with open(tts_filepath, "wb") as f:
            f.write(audio_bytes)
        tts_audio_url = f"/static/audio_cache/{tts_filename}"
    except Exception as e:
        print(f"TTS Summary Generation Error: {e}")
        tts_audio_url = "/static/audio_cache/error.wav"
        
    return {
        "status": "success",
        "data": summary,
        "tts_audio_url": tts_audio_url,
        "message": spoken_text
    }

# --- WhatsApp Reminders Nudge generator ---
@app.get("/api/reminders")
def api_get_reminders():
    debtors = get_outstanding_reminders()
    processed_reminders = []
    
    for debtor in debtors:
        customer_name = debtor["customer_name"]
        phone = debtor["phone_number"] or "9100000000" # Placeholder if none exists
        amount = debtor["amount_owed"]
        days = debtor["days_pending"]
        
        # Clean phone formatting
        clean_phone = "".join(filter(str.isdigit, phone))
        if len(clean_phone) == 10:
            clean_phone = f"91{clean_phone}" # default country code India
            
        message = (
            f"Namaste {customer_name} ji, aapka Dukaan pe Rs. {amount:.2f} ka "
            f"udhaar pending hai jo {days} dino se bacha hai. Kripya isey clear karein. Dhanyawaad!"
        )
        encoded_message = urllib.parse.quote(message)
        wa_link = f"https://wa.me/{clean_phone}?text={encoded_message}"
        
        processed_reminders.append({
            "customer_name": customer_name,
            "phone_number": phone,
            "amount_owed": amount,
            "days_pending": days,
            "whatsapp_link": wa_link,
            "message_text": message
        })
        
    return {
        "status": "success",
        "reminders": processed_reminders
    }

# --- CSV DB Data Export / Backup ---
@app.get("/api/export")
def api_export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 1. Export Inventory Table
    writer.writerow(["--- INVENTORY DATA ---"])
    writer.writerow(["ID", "Item Name", "Quantity", "Cost Price", "Selling Price", "Low Stock Threshold", "Last Updated"])
    items = get_inventory()
    for item in items:
        writer.writerow([
            item.get("id"), item.get("item_name"), item.get("quantity"),
            item.get("cost_price"), item.get("selling_price"),
            item.get("low_stock_threshold"), item.get("updated_at")
        ])
        
    writer.writerow([]) # empty row separator
    
    # 2. Export Ledger Table
    writer.writerow(["--- LEDGER DATA ---"])
    writer.writerow(["ID", "Customer Name", "Phone Number", "Amount (+ve Credit, -ve Payment)", "Reason / Product", "Created At"])
    ledger_entries = get_ledger()
    for entry in ledger_entries:
        writer.writerow([
            entry.get("id"), entry.get("customer_name"), entry.get("phone_number"),
            entry.get("amount"), entry.get("reason"), entry.get("created_at")
        ])
        
    response = StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = "attachment; filename=dukaan_voice_backup.csv"
    return response

# Serve static web assets directly
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
