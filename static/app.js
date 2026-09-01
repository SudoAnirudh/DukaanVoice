// Application State
let currentPin = "";
let mediaRecorder = null;
let audioChunks = [];
let recordingInterval = null;
let recordSeconds = 0;
let isRecording = false;
let audioContext = null;
let analyser = null;
let dataArray = null;
let animationFrameId = null;

// DOM Elements
const pinOverlay = document.getElementById("pin-overlay");
const appContainer = document.getElementById("app-container");
const pinDots = document.querySelectorAll(".dot");
const pinError = document.getElementById("pin-error");
const micBtn = document.getElementById("mic-btn");
const micInstruction = document.getElementById("mic-instruction");
const recordingTime = document.getElementById("recording-time");
const ttsAudio = document.getElementById("tts-audio");
const canvas = document.getElementById("waveform-canvas");
const canvasCtx = canvas.getContext("2d");

// Initialize Canvas Sizing
function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();

// --- 1. PIN Keypad Code ---
function pressPin(digit) {
    if (currentPin.length < 4) {
        currentPin += digit;
        updatePinDots();
    }
}

function clearPin() {
    currentPin = "";
    updatePinDots();
    pinError.classList.remove("visible");
}

function updatePinDots() {
    pinDots.forEach((dot, idx) => {
        if (idx < currentPin.length) {
            dot.classList.add("active");
        } else {
            dot.classList.remove("active");
        }
    });
}

async function submitPin() {
    if (currentPin.length !== 4) return;
    
    try {
        const response = await fetch("/api/verify-pin", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pin: currentPin })
        });
        
        const data = await response.json();
        
        if (response.ok && data.authenticated) {
            if (data.token) {
                localStorage.setItem("dukaanvoice_token", data.token);
            }
            pinOverlay.classList.add("hidden");
            appContainer.classList.remove("hidden");
            // Load dashboard data
            fetchData();
            // Start visualizer idle animation
            drawIdleWaveform();
        } else {
            showPinError();
        }
    } catch (e) {
        showPinError();
    }
}

function getAuthHeaders() {
    const token = localStorage.getItem("dukaanvoice_token");
    return token ? { "Authorization": `Bearer ${token}` } : {};
}


function showPinError() {
    pinError.classList.add("visible");
    currentPin = "";
    updatePinDots();
}

function lockApp() {
    appContainer.classList.add("hidden");
    pinOverlay.classList.remove("hidden");
    clearPin();
}

// --- 2. Dashboard Data Loading ---
async function fetchData() {
    await Promise.all([
        fetchInventory(),
        fetchLedger(),
        fetchReminders()
    ]);
}

async function fetchInventory() {
    try {
        const response = await fetch("/api/inventory", { headers: getAuthHeaders() });
        const items = await response.json();
        
        const tbody = document.getElementById("inventory-list");
        tbody.innerHTML = "";
        document.getElementById("inv-count").innerText = `${items.length} Items`;
        
        items.forEach(item => {
            const margin = item.selling_price - item.cost_price;
            const marginPercent = item.selling_price > 0 ? ((margin / item.selling_price) * 100).toFixed(0) : 0;
            
            const isLow = item.quantity <= item.low_stock_threshold;
            const statusClass = isLow ? "status-tag low" : "status-tag ok";
            const statusText = isLow ? "LOW STOCK" : "IN STOCK";
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${item.item_name}</strong></td>
                <td>${item.quantity}</td>
                <td>₹${item.cost_price.toFixed(2)}</td>
                <td>₹${item.selling_price.toFixed(2)}</td>
                <td>₹${margin.toFixed(2)} (${marginPercent}%)</td>
                <td><span class="${statusClass}">${statusText}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading inventory", e);
    }
}

async function fetchLedger() {
    try {
        const response = await fetch("/api/ledger", { headers: getAuthHeaders() });
        const entries = await response.json();
        
        // Sum balances per customer
        const customerMap = {};
        entries.forEach(entry => {
            const name = entry.customer_name;
            if (!customerMap[name]) {
                customerMap[name] = {
                    name: name,
                    phone: entry.phone_number || "-",
                    balance: 0.0
                };
            }
            customerMap[name].balance += entry.amount;
        });
        
        const tbody = document.getElementById("ledger-list");
        tbody.innerHTML = "";
        
        const uniqueCustomers = Object.values(customerMap);
        document.getElementById("ledger-count").innerText = `${uniqueCustomers.length} Accounts`;
        
        uniqueCustomers.forEach(cust => {
            const balClass = cust.balance > 0 ? "amt-credit" : "amt-paid";
            const balPrefix = cust.balance > 0 ? "+" : "";
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${cust.name}</strong></td>
                <td>${cust.phone}</td>
                <td><span class="${balClass}">${balPrefix}₹${cust.balance.toFixed(2)}</span></td>
                <td><span class="status-tag ${cust.balance > 0 ? 'low' : 'ok'}">${cust.balance > 0 ? 'DUE' : 'CLEAR'}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading ledger", e);
    }
}

async function fetchReminders() {
    try {
        const response = await fetch("/api/reminders", { headers: getAuthHeaders() });
        const res = await response.json();

        
        const container = document.getElementById("reminders-list");
        container.innerHTML = "";
        
        // Filter outstanding debtor transactions > 15 days pending
        const reminders = res.reminders.filter(r => r.days_pending >= 15);
        
        if (reminders.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; color: var(--text-secondary); padding: 20px;">
                    <i class="fa-solid fa-square-check" style="font-size: 2rem; color: var(--success); margin-bottom: 8px;"></i>
                    <p>No overdue credits pending nudges.</p>
                </div>
            `;
            return;
        }
        
        reminders.forEach(rem => {
            const card = document.createElement("div");
            card.className = "reminder-card";
            card.innerHTML = `
                <div class="reminder-info">
                    <h4>${rem.customer_name}</h4>
                    <p>${rem.phone_number ? rem.phone_number : 'No Phone'} • <strong>Pending ${rem.days_pending} days</strong></p>
                </div>
                <div class="reminder-actions">
                    <span class="reminder-debt">₹${rem.amount_owed.toFixed(2)}</span>
                    <button class="wa-nudge-btn" onclick="sendWhatsappNudge('${rem.whatsapp_link}')" title="Send WhatsApp reminder text">
                        <i class="fa-brands fa-whatsapp"></i>
                    </button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Error loading reminders", e);
    }
}

function sendWhatsappNudge(link) {
    window.open(link, "_blank");
}

// --- 3. Speech Audio Recording ---
async function startRecording() {
    if (isRecording) return;
    
    // Request microphone permission
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        isRecording = true;
        audioChunks = [];
        
        // UI feedback changes
        micBtn.classList.add("recording");
        micInstruction.innerText = "Listening... Release button to complete";
        recordingTime.classList.remove("hidden");
        recordingTime.innerText = "00:00";
        
        // Start timers
        recordSeconds = 0;
        recordingInterval = setInterval(() => {
            recordSeconds++;
            const minutes = Math.floor(recordSeconds / 60).toString().padStart(2, "0");
            const seconds = (recordSeconds % 60).toString().padStart(2, "0");
            recordingTime.innerText = `${minutes}:${seconds}`;
        }, 1000);
        
        // Setup Media Recorder
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = event => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = uploadAudioPayload;
        
        // Setup Live Canvas Web Audio Analyzer
        setupAudioAnalyser(stream);
        
        mediaRecorder.start();
        
    } catch (err) {
        console.error("Microphone access denied:", err);
        alert("Please allow mic access to record voice commands.");
        isRecording = false;
    }
}

function stopRecording() {
    if (!isRecording) return;
    
    isRecording = false;
    micBtn.classList.remove("recording");
    micInstruction.innerText = "Processing voice command...";
    recordingTime.classList.add("hidden");
    
    clearInterval(recordingInterval);
    
    if (mediaRecorder) {
        mediaRecorder.stop();
        // Stop audio tracks
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    
    // Stop Analyser frame loops
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
    }
    drawIdleWaveform();
}

function setupAudioAnalyser(stream) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);
    
    analyser.fftSize = 256;
    const bufferLength = analyser.frequencyBinCount;
    dataArray = new Uint8Array(bufferLength);
    
    drawWaveform();
}

// Draw real-time mic input LED Bargraph
function drawWaveform() {
    if (!isRecording) return;
    
    animationFrameId = requestAnimationFrame(drawWaveform);
    analyser.getByteFrequencyData(dataArray);
    
    resizeCanvas();
    canvasCtx.clearRect(0, 0, canvas.width, canvas.height);
    
    const numBars = 36;
    const barWidth = canvas.width / numBars;
    const gap = 6;
    const segmentsPerBar = 12;
    const segmentGap = 2;
    const segmentHeight = (canvas.height - (segmentsPerBar * segmentGap)) / segmentsPerBar;
    
    for (let i = 0; i < numBars; i++) {
        const freqIndex = Math.floor((i / numBars) * dataArray.length * 0.65);
        const rawVal = dataArray[freqIndex];
        const val = rawVal / 255.0;
        
        const activeSegments = Math.round(val * segmentsPerBar);
        const x = i * barWidth + gap / 2;
        
        for (let s = 0; s < segmentsPerBar; s++) {
            const y = canvas.height - (s + 1) * (segmentHeight + segmentGap);
            let color = "rgba(255, 255, 255, 0.02)"; // VFD off grid segment
            
            if (s < activeSegments) {
                if (s < 7) {
                    color = "rgba(16, 185, 129, 0.9)"; // Green VFD
                } else if (s < 10) {
                    color = "rgba(234, 179, 8, 0.9)"; // Amber warning
                } else {
                    color = "rgba(239, 68, 68, 0.9)"; // Red peak line
                }
            }
            
            canvasCtx.fillStyle = color;
            canvasCtx.fillRect(x, y, barWidth - gap, segmentHeight);
        }
    }
}

// Draw VFD oscilloscope reference grids when idle
function drawIdleWaveform() {
    resizeCanvas();
    canvasCtx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw oscilloscope grids
    canvasCtx.strokeStyle = "rgba(255, 255, 255, 0.015)";
    canvasCtx.lineWidth = 1;
    const step = 12;
    
    for (let x = 0; x < canvas.width; x += step) {
        canvasCtx.beginPath();
        canvasCtx.moveTo(x, 0);
        canvasCtx.lineTo(x, canvas.height);
        canvasCtx.stroke();
    }
    for (let y = 0; y < canvas.height; y += step) {
        canvasCtx.beginPath();
        canvasCtx.moveTo(0, y);
        canvasCtx.lineTo(canvas.width, y);
        canvasCtx.stroke();
    }
    
    // Draw green reference center line
    canvasCtx.beginPath();
    canvasCtx.strokeStyle = "rgba(16, 185, 129, 0.25)";
    canvasCtx.lineWidth = 1.5;
    canvasCtx.moveTo(0, canvas.height / 2);
    canvasCtx.lineTo(canvas.width, canvas.height / 2);
    canvasCtx.stroke();
}

async function uploadAudioPayload() {
    const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
    const formData = new FormData();
    formData.append("audio_file", audioBlob, "command.wav");
    
    // Receipt Elements
    const logBox = document.getElementById("feed-log");
    const logTranscript = document.getElementById("log-transcription");
    const logIntent = document.getElementById("log-intent");
    const logEntities = document.getElementById("log-entities");
    const receiptTime = document.getElementById("receipt-timestamp");
    
    // Add paper printing animation classes
    logBox.classList.add("printing");
    receiptTime.innerText = new Date().toLocaleTimeString("en-IN", { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + " " + new Date().toLocaleDateString("en-IN");
    logTranscript.innerText = "Processing audio command...";
    logIntent.innerText = "PROCESSING...";
    logIntent.className = "value-badge processing";
    logEntities.innerText = "WAITING FOR PARSER";
    
    try {
        const response = await fetch("/api/voice-command", {
            method: "POST",
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.status === "success") {
            logTranscript.innerText = `"${data.transcription}"`;
            
            const intent = data.parsed_command.intent;
            logIntent.innerText = intent;
            logIntent.className = `value-badge ${intent === 'UNKNOWN' ? 'intent-unknown' : 'intent-ok'}`;
            
            const ent = data.parsed_command.entities;
            let displayEnt = "";
            if (intent.includes("STOCK")) {
                displayEnt = `${ent.item_name || 'Item'}: Qty ${ent.quantity || 1}`;
            } else if (intent.includes("CREDIT") || intent.includes("PAYMENT")) {
                displayEnt = `${ent.customer_name || 'Customer'}: ₹${(ent.amount || 0.0).toFixed(2)}`;
            } else {
                displayEnt = "-";
            }
            logEntities.innerText = displayEnt;
            
            playTtsAudio(data.tts_audio_url);
            fetchData();
        } else {
            logTranscript.innerText = "Command not parsed. Please try again.";
            logIntent.innerText = "PARSE_ERROR";
            logIntent.className = "value-badge intent-unknown";
            logEntities.innerText = "ERR";
            playTtsAudio("/static/audio_cache/error.wav");
        }
    } catch (err) {
        console.error("Upload failed:", err);
        logTranscript.innerText = "Network transmission failed.";
        logIntent.innerText = "NET_ERROR";
        logIntent.className = "value-badge intent-unknown";
        logEntities.innerText = "OFFLINE";
        playTtsAudio("/static/audio_cache/error.wav");
    } finally {
        micInstruction.innerText = "Click & Hold Spacebar or Button to Speak";
        // Let print animation complete and settle
        setTimeout(() => {
            logBox.classList.remove("printing");
        }, 1200);
    }
}

function playTtsAudio(url) {
    ttsAudio.src = url;
    ttsAudio.play().catch(e => console.log("TTS play deferred", e));
}

async function playDailySummary() {
    const summaryBtn = document.getElementById("btn-summary");
    summaryBtn.disabled = true;
    summaryBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Printing Summary...`;
    
    const logBox = document.getElementById("feed-log");
    const logTranscript = document.getElementById("log-transcription");
    const logIntent = document.getElementById("log-intent");
    const logEntities = document.getElementById("log-entities");
    const receiptTime = document.getElementById("receipt-timestamp");
    
    logBox.classList.add("printing");
    receiptTime.innerText = new Date().toLocaleTimeString("en-IN", { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + " " + new Date().toLocaleDateString("en-IN");
    
    try {
        const response = await fetch("/api/daily-summary");
        const res = await response.json();
        
        if (response.ok && res.status === "success") {
            playTtsAudio(res.tts_audio_url);
            logTranscript.innerText = res.message;
            logIntent.innerText = "EOD_SUMMARY";
            logIntent.className = "value-badge intent-ok";
            logEntities.innerText = `Sales: ₹${res.data.total_sales.toFixed(2)}`;
        }
    } catch (e) {
        console.error(e);
    } finally {
        summaryBtn.disabled = false;
        summaryBtn.innerHTML = `<i class="fa-solid fa-chart-line"></i> Play Today's Summary`;
        setTimeout(() => {
            logBox.classList.remove("printing");
        }, 1200);
    }
}

// --- 5. Key Event bindings (Spacebar to Record) ---
let isSpacePressed = false;
window.addEventListener("keydown", (e) => {
    // Only bind spacebar when App is unlocked and not typing inside input if any
    const isOverlayOpen = !pinOverlay.classList.contains("hidden");
    if (e.code === "Space" && !isOverlayOpen && !isSpacePressed) {
        e.preventDefault();
        isSpacePressed = true;
        startRecording();
    }
});

window.addEventListener("keyup", (e) => {
    if (e.code === "Space" && isSpacePressed) {
        e.preventDefault();
        isSpacePressed = false;
        stopRecording();
    }
});
