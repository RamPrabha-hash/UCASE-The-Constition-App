const input = document.getElementById("userInput");
const chat = document.getElementById("chat");
function requestOTP() {
    const mobile = document.getElementById("mobile").value;

    if (!mobile) {
        alert("Please enter mobile number");
        return;
    }

    fetch("/request-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mobile: mobile })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("OTP sent successfully (check console)");
        } else {
            alert("Failed to send OTP");
        }
    })
    .catch(err => {
        console.error(err);
        alert("Server error");
    });
}


function addMessage(text, sender) {
    const msg = document.createElement("div");
    msg.className = `message ${sender}`;
    msg.innerHTML = `<div class="bubble">${text}</div>`;
    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
}

function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, "user");
    input.value = "";

    fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
        addMessage(data.reply, "bot");
    })
    .catch(() => {
        addMessage("Server error. Please try again.", "bot");
    });
}

input.addEventListener("keypress", e => {
    if (e.key === "Enter") sendMessage();
});

function newChat() {
    chat.innerHTML = "";
}

// --- VOICE RECORDING LOGIC ---
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

async function toggleRecording() {
    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }
}

async function startRecording() {
    const micBtn = document.getElementById("micBtn");
    const recStatus = document.getElementById("recStatus");
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            audioChunks = [];
            sendAudioToBackend(audioBlob);
            stream.getTracks().forEach(t => t.stop()); // release mic
        };
        
        mediaRecorder.start();
        isRecording = true;
        micBtn.innerHTML = "⏹️"; 
        recStatus.style.display = "inline";
    } catch (err) {
        console.error("Microphone access denied: ", err);
        alert("Microphone access denied or not available.");
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        document.getElementById("micBtn").innerHTML = "🎤";
        document.getElementById("recStatus").style.display = "none";
    }
}

function sendAudioToBackend(audioBlob) {
    // Show a loading/processing message for the user
    addMessage("🎤 <i>Audio Message Sent...</i>", "user");
    
    const formData = new FormData();
    formData.append("audio_data", audioBlob, "voice_msg.webm");
    
    fetch("/api/chat_audio", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.reply) {
            addMessage(data.reply, "bot");
        } else if (data.error) {
            addMessage("⚠️ " + data.error, "bot");
        }
    })
    .catch(err => {
        console.error(err);
        addMessage("Server error while processing audio. Please try again.", "bot");
    });
}

