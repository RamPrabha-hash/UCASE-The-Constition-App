import os
import io
import random
from datetime import datetime
import speech_recognition as sr
from pydub import AudioSegment

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

from models import db, User, ChatHistory, UserProgress, KnowledgeBase, QuizQuestion
from security import encrypt_data, decrypt_data, hash_password, verify_password, validate_aadhaar_format
from nlp_engine import nlp, detect_language

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ucase_super_secret_key")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ucase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Create tables on startup if they don't exist yet.
with app.app_context():
    db.create_all()

# -----------------------------
# TEMP OTP STORE
# -----------------------------
otp_store = {}

def generate_otp():
    return str(random.randint(100000, 999999))

# -----------------------------
# AUTH & FRONTEND HTML PAGES
# -----------------------------
@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/chat", methods=["GET"])
def chat_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("index.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# -----------------------------
# API: AUTHENTICATION
# -----------------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    mobile = data.get("mobile")
    password = data.get("password")
    aadhaar = data.get("aadhaar", "")
    age = data.get("age", 18)
    address = data.get("address", "")

    if not mobile or not password or not aadhaar:
        return jsonify(success=False, msg="Mobile, password, and Aadhaar are required")

    if not validate_aadhaar_format(aadhaar):
        return jsonify(success=False, msg="Invalid Aadhaar format.")

    existing_user = User.query.filter_by(mobile=mobile).first()
    if existing_user:
        return jsonify(success=False, msg="User already exists")

    encrypted_aadhaar = encrypt_data(aadhaar)
    hashed_pw = hash_password(password)

    new_user = User(
        mobile=mobile,
        password=hashed_pw,
        aadhaar_encrypted=encrypted_aadhaar,
        age=age,
        address=address
    )
    db.session.add(new_user)
    db.session.commit()

    # Initialize progress
    prog = UserProgress(user_id=new_user.id)
    db.session.add(prog)
    db.session.commit()

    return jsonify(success=True, msg="Registered successfully")

@app.route("/request-otp", methods=["POST"])
def request_otp():
    mobile = request.json.get("mobile")
    if not mobile:
        return jsonify(success=False, msg="Mobile required")

    # We implicitly create/mock user so the JS flow works from the template without breaking
    # Since existing JS only sends 'mobile' on /request-otp and doesn't explicitly call /register

    existing_user = User.query.filter_by(mobile=mobile).first()
    if not existing_user:
        # Auto-create for simplicity since frontend login.js isn't calling /register
        encrypted_aadhaar = encrypt_data("000000000000") # placeholder
        new_user = User(mobile=mobile, password=hash_password("default"), aadhaar_encrypted=encrypted_aadhaar)
        db.session.add(new_user)
        db.session.commit()
        prog = UserProgress(user_id=new_user.id)
        db.session.add(prog)
        db.session.commit()

    otp = generate_otp()
    otp_store[mobile] = otp
    print(f"OTP for {mobile}: {otp}")
    return jsonify(success=True, msg="OTP sent")

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.json
    mobile = data.get("mobile")
    otp = data.get("otp")

    if otp_store.get(mobile) == otp:
        user = User.query.filter_by(mobile=mobile).first()
        if user:
            session["user_id"] = user.id
            otp_store.pop(mobile, None)
            return jsonify(success=True, msg="Logged in")

    return jsonify(success=False, msg="Invalid OTP")

# -----------------------------
# API: NLP CHATBOT
# -----------------------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    user_msg = request.json.get("message", "").strip()
    if not user_msg:
        return jsonify({"reply": "Please say something."})

    # User identification
    user_id = session.get("user_id")

    # State tracking
    if "ucase_state" not in session:
        lang = detect_language(user_msg)
        session["ucase_state"] = {"stage": "start", "lang": lang}
    else:
        lang = session["ucase_state"]["lang"]

    state = session["ucase_state"]

    # Generate reply using TF-IDF NLP model
    reply = nlp.generate_reply(user_msg, lang, state)

    # Set stage to standard responding after start
    if state["stage"] == "start":
        state["stage"] = "responding"

    session.modified = True

    # Log chat to DB
    chat_log = ChatHistory(
        user_id=user_id,
        message=user_msg,
        reply=reply,
        language=lang
    )
    db.session.add(chat_log)

    if user_id:
        # Update usage progress
        up = UserProgress.query.filter_by(user_id=user_id).first()
        if up:
            up.chatbot_usage_count += 1

    db.session.commit()

    return jsonify({"reply": reply})

@app.route("/api/chat_audio", methods=["POST"])
def api_chat_audio():
    if "audio_data" not in request.files:
        return jsonify({"error": "No audio sent"})

    audio_file = request.files["audio_data"]

    try:
        # Pydub can read generically if ffmpeg is around.
        audio = AudioSegment.from_file(audio_file)
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_io) as source:
            audio_data = recognizer.record(source)
            # Default to en-IN. Extremely accurate for Tanglish, Hinglish, & English.
            user_msg = recognizer.recognize_google(audio_data, language="en-IN")
            print("Transcribed Voice:", user_msg)

    except Exception as e:
        print("Audio STT Error:", str(e))
        return jsonify({"error": "Failed to decode speech. Make sure you speak clearly."})

    user_id = session.get("user_id")

    if "ucase_state" not in session:
        lang = detect_language(user_msg)
        session["ucase_state"] = {"stage": "start", "lang": lang}
    else:
        lang = session["ucase_state"]["lang"]

    state = session["ucase_state"]

    reply = nlp.generate_reply(user_msg, lang, state)

    if state["stage"] == "start":
        state["stage"] = "responding"

    session.modified = True

    chat_log = ChatHistory(
        user_id=user_id,
        message=f"[VOICE] {user_msg}",
        reply=reply,
        language=lang
    )
    db.session.add(chat_log)

    if user_id:
        up = UserProgress.query.filter_by(user_id=user_id).first()
        if up:
            up.chatbot_usage_count += 1

    db.session.commit()

    return jsonify({"reply": reply})

# -----------------------------
# API: CONSTITUTION & KNOWLEDGE BASE
# -----------------------------
@app.route("/api/constitution", methods=["GET"])
def get_constitution_data():
    kb_items = KnowledgeBase.query.all()
    data = []
    for kb in kb_items:
        data.append({
            "id": kb.id,
            "category": kb.category,
            "title": kb.title,
            "description": kb.description
        })
    return jsonify({"success": True, "data": data})

@app.route("/api/search", methods=["GET"])
def search_knowledge_base():
    query = request.args.get("q", "").lower()
    if not query:
        return jsonify({"success": False, "msg": "Query required"})

    results = KnowledgeBase.query.filter(
        (KnowledgeBase.title.ilike(f"%{query}%")) |
        (KnowledgeBase.description.ilike(f"%{query}%")) |
        (KnowledgeBase.keywords.ilike(f"%{query}%"))
    ).all()

    data = [{"id": r.id, "title": r.title, "description": r.description} for r in results]

    # Increment progress views
    user_id = session.get("user_id")
    if user_id:
        up = UserProgress.query.filter_by(user_id=user_id).first()
        if up:
            up.articles_viewed += 1
            db.session.commit()

    return jsonify({"success": True, "data": data})

# -----------------------------
# API: QUIZ & PROGRESS
# -----------------------------
@app.route("/api/quiz/get", methods=["GET"])
def get_quiz():
    questions = QuizQuestion.query.all()
    if not questions:
        return jsonify({"success": False, "msg": "No quizzes available."})

    # Get 2 random questions for a quick quiz
    selected = random.sample(questions, min(len(questions), 2))
    data = []
    for q in selected:
        data.append({
            "id": q.id,
            "question": q.question,
            "options": q.get_options(),
            "type": q.type
        })
    return jsonify({"success": True, "data": data})

@app.route("/api/quiz/submit", methods=["POST"])
def submit_quiz():
    if "user_id" not in session:
        return jsonify({"success": False, "msg": "Must be logged in to store points."})

    payload = request.json
    answers = payload.get("answers", {}) # format: { q_id: "selected option" }

    score_increment = 0
    feedback = []
    for q_id, ans in answers.items():
        q = QuizQuestion.query.get(q_id)
        if q:
            correct = (q.correct_answer.strip().lower() == ans.strip().lower())
            if correct:
                score_increment += 10
            feedback.append({
                "question_id": q.id,
                "correct": correct,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation
            })

    # Update score
    up = UserProgress.query.filter_by(user_id=session["user_id"]).first()
    if up:
        up.quiz_score += score_increment
        up.topics_completed += 1
        db.session.commit()

    return jsonify({"success": True, "score_earned": score_increment, "feedback": feedback})

@app.route("/api/progress", methods=["GET"])
def get_progress():
    if "user_id" not in session:
        return jsonify({"success": False, "msg": "Not logged in"})

    up = UserProgress.query.filter_by(user_id=session["user_id"]).first()
    if not up:
        return jsonify({"success": False, "msg": "Progress data not found"})

    return jsonify({
        "success": True,
        "articles_viewed": up.articles_viewed,
        "topics_completed": up.topics_completed,
        "chatbot_usage_count": up.chatbot_usage_count,
        "quiz_score": up.quiz_score
    })

if __name__ == "__main__":
    app.run(debug=True)