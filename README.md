# 🏪 DukaanVoice (दुकानवॉइस)

> **Voice-First Kirana Store Management & Digital Khata powered by Sarvam AI**

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Sarvam AI](https://img.shields.io/badge/Sarvam_AI-Saaras_|_Bulbul_|_30B-6C5CE7?style=flat)](https://www.sarvam.ai/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Deploy on Render](https://img.shields.io/badge/Render-Deploy_Ready-46E3B7?style=flat&logo=render&logoColor=white)](https://render.com/)

**DukaanVoice** is a multilingual, voice-enabled store management and digital ledger system built specifically for Indian Kirana (grocery) shopkeepers. By combining high-accuracy speech recognition, natural language understanding, and regional text-to-speech synthesis, shopkeepers can manage stock levels, log credit (*udhaar*), receive voice alerts for low stock, send WhatsApp payment reminders, and listen to End-of-Day (EOD) business summaries—all using natural voice commands in their native languages.

---

## 🌟 Key Features

- 🎙️ **Multilingual Voice Commands (Sarvam Saaras STT)**
  - Auto-detects 10+ Indian languages and code-mixed speech (Hindi, Tamil, Malayalam, Bengali, Telugu, Gujarati, Kannada, Marathi, Punjabi, Odia, Indian English).
- 🧠 **NLU & Intent Extraction (Sarvam-30B LLM)**
  - Converts spoken phrases into structured JSON intents (`ADD_STOCK`, `REMOVE_STOCK`, `LOG_CREDIT`, `LOG_PAYMENT`, `QUERY_STOCK`, `QUERY_BALANCE`).
- 🔊 **Voice Feedback & Inquiry Responses (Sarvam Bulbul v3 TTS)**
  - Speaks back natural confirmation responses, stock level queries, customer balances, and low-stock warnings in the user's detected language.
- 🔍 **Fuzzy Matching & Name Normalization (`rapidfuzz`)**
  - Resolves minor variations and typos in item and customer names (e.g. *"Maggie"* $\rightarrow$ *"Maggi Noodles"*, *"Rameshbhai"* $\rightarrow$ *"Ramesh Kumar"*).
- 📈 **Gross Profit & Business Analytics**
  - Tracks profit margins per item (`selling_price - cost_price`) and calculates daily gross profit estimates.
- 📱 **Progressive Web App (PWA) Mobile Installation**
  - Includes `manifest.json` and service worker (`sw.js`) for home screen installation on mobile devices.
- 📖 **Digital Khata & Ledger Management**
  - Tracks customer credit balances, transaction histories, and days pending for unpaid balances.
- 📲 **WhatsApp Udhaar Nudge Generator**
  - Auto-generates personalized `wa.me` links pre-filled with courteous payment reminder messages.
- 📊 **Voice-Powered End-of-Day (EOD) Summary**
  - Generates spoken summaries of daily cash sales, credit issued, gross profit, and top-selling products.
- 💾 **CSV Export & Local Backup**
  - Download complete inventory and customer ledger records in a single CSV file with one click.
- 🔒 **JWT & PIN-Gated Access**
  - Secure shop access with PIN verification and session JWT authorization tokens.


---

## 🏗️ Architecture & Tech Stack

```
           [ Web UI / Microphone ]
                      │
                      ▼
               ( WAV Audio )
                      │
                      ▼
  ┌────────────────────────────────────────┐
  │       FastAPI Application Backend      │
  │────────────────────────────────────────│
  │ 1. Sarvam Saaras (v3 STT)             │ ──► Transcribe & Detect Lang
  │ 2. Sarvam 30B LLM (NLU Engine)         │ ──► Extract Intent & Entities
  │ 3. SQLite Database (Inventory & Khata) │ ──► Update Stock & Ledger
  │ 4. Sarvam Bulbul (v3 TTS)              │ ──► Generate Audio Response
  └────────────────────────────────────────┘
                      │
                      ▼
        ( Audio URL & Spoken Confirmation )
```

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11)
- **Database**: SQLite 3 (Lightweight embedded transactional database)
- **AI Integrations (Sarvam AI APIs)**:
  - Speech-to-Text: `saaras:v3` (Code-mixed language support)
  - Intent Extraction: `sarvam-30b` Chat Completions API
  - Text-to-Speech: `bulbul:v3` (`ritu` speaker model, 24kHz)
- **Frontend**: Vanilla HTML5, CSS3, JavaScript (Web Audio API for microphone capture)
- **Deployment**: Docker containerized, Render PaaS blueprint included

---

## 📁 Directory Structure

```
DukaanVoice/
├── main.py              # FastAPI application, route handlers, & orchestration
├── database.py          # SQLite database schema, CRUD operations, & queries
├── sarvam_client.py     # Sarvam AI API client (STT, LLM, TTS)
├── seed_db.py           # Database seeder script with sample Kirana data
├── test_sarvam_api.py   # Utility script to test Sarvam API authorization
├── requirements.txt     # Python project dependencies
├── Dockerfile           # Multi-stage Docker container specification
├── render.yaml          # Render PaaS deployment blueprint config
├── .env                 # Environment variables configuration file
└── static/              # Frontend static web assets
    ├── index.html       # Web app interface
    ├── styles.css       # UI styling
    ├── app.js           # Frontend logic, audio recording, & API calls
    └── audio_cache/     # Temporary TTS audio file cache
```

---

## ⚙️ Prerequisites & Environment Setup

### Prerequisites
- Python **3.10+** (Python 3.11 recommended)
- A valid **Sarvam AI Subscription Key** ([Get your API Key from Sarvam AI](https://www.sarvam.ai/))

### Environment Variables

Create a `.env` file in the root directory:

```env
# Required: Your Sarvam AI API Subscription Key
SARVAM_API_KEY=your_sarvam_api_key_here

# Optional: Shop security PIN code (Default: 1234)
SHOP_PIN=1234

# Optional: Application port (Default: 8000)
PORT=8000
```

---

## 🚀 Quick Start (Local Development)

### 1. Clone the repository
```bash
git clone https://github.com/your-username/DukaanVoice.git
cd DukaanVoice
```

### 2. Create and activate a virtual environment
```bash
# On Linux/macOS
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Seed the Database (Optional but recommended)
Populate the SQLite database with sample Kirana items (Maggi, Amul Butter, Surf Excel) and customer ledger entries:
```bash
python seed_db.py
```

### 5. Verify Sarvam AI API Connection
```bash
python test_sarvam_api.py
```

### 6. Run Automated Tests
```bash
PYTHONPATH=. pytest tests/
```

### 7. Run the Application
```bash
uvicorn main:app --reload --port 8000
```
Open your browser and navigate to **`http://localhost:8000`**.


---

## 🐳 Docker Setup

### Build the Image
```bash
docker build -t dukaanvoice .
```

### Run the Container
```bash
docker run -d \
  -p 8000:8000 \
  -e SARVAM_API_KEY="your_sarvam_api_key_here" \
  -e SHOP_PIN="1234" \
  --name dukaanvoice_app \
  dukaanvoice
```
Access the application at `http://localhost:8000`.

---

## 🌐 Deploy to Render

The repository includes a pre-configured `render.yaml` blueprint.

1. Push code to your GitHub repository.
2. Go to **Render Dashboard** -> **New** -> **Blueprint**.
3. Connect your repository.
4. Set the `SARVAM_API_KEY` environment variable when prompted.
5. Deploy!

---

## 🗣️ Example Voice Commands

| Intent | Spoken Example (Hinglish / Regional) | Action Taken |
| :--- | :--- | :--- |
| **`ADD_STOCK`** | *"Stock mein 10 packet Maggi daalo"* | Increases Maggi stock by 10 |
| **`REMOVE_STOCK`** | *"Maggi ke 2 packet kam karo"* | Decreases Maggi stock by 2 (triggers warning if stock <= threshold) |
| **`LOG_CREDIT`** | *"Ramesh ko 150 rupees ki udhaar do"* | Adds ₹150 credit entry under Ramesh Kumar's ledger |
| **`LOG_PAYMENT`** | *"Ramesh ne 100 rupees pay kiye"* | Records ₹100 payment received from Ramesh |

---

## 📡 API Reference

### Auth
- `POST /api/verify-pin`
  - Validates shop PIN code.

### Inventory & Ledger
- `GET /api/inventory` — List all stock items, quantities, prices, and low-stock alerts.
- `GET /api/ledger` — Fetch complete customer credit and payment ledger history.

### Voice & Automation
- `POST /api/voice-command` — Uploads microphone `.wav` audio, processes STT/NLU/TTS pipeline, updates database, and returns audio confirmation URL.
- `GET /api/daily-summary` — Calculates EOD cash sales, credit issued, top items, and returns audio summary.
- `GET /api/reminders` — Fetches outstanding debtors and returns WhatsApp message deep-links.
- `GET /api/export` — Streams full inventory and ledger backup as a `.csv` file.

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.
