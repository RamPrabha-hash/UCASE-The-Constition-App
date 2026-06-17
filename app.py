import os
import io
import random
from datetime import datetime
from pydub import AudioSegment

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

from models import db, User, ChatHistory, UserProgress, KnowledgeBase, QuizQuestion
from security import encrypt_data, decrypt_data, hash_password, verify_password, validate_aadhaar_format
from nlp_engine import nlp, detect_language


# -----------------------------
# FLASK APP INIT (ONLY ONCE)
# -----------------------------
app = Flask(__name__)
app.secret_key = "ucase_super_secret_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ucase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# -----------------------------
# TEMP OTP STORE
# -----------------------------
otp_store = {}

def generate_otp():
    return str(random.randint(100000, 999999))


# -----------------------------
# FRONTEND PAGES
# -----------------------------
@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/chat")
def chat_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("index.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


# -----------------------------
# AUTH: REGISTER
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
        return jsonify(success=False, msg="Required fields missing")

    if not validate_aadhaar_format(aadhaar):
        return jsonify(success=False, msg="Invalid Aadhaar format")

    if User.query.filter_by(mobile=mobile).first():
        return jsonify(success=False, msg="User already exists")

    new_user = User(
        mobile=mobile,
        password=hash_password(password),
        aadhaar_encrypted=encrypt_data(aadhaar),
        age=age,
        address=address
    )

    db.session.add(new_user)
    db.session.commit()

    db.session.add(UserProgress(user_id=new_user.id))
    db.session.commit()

    return jsonify(success=True, msg="Registered successfully")


# -----------------------------
# OTP LOGIN
# -----------------------------
@app.route("/request-otp", methods=["POST"])
def request_otp():
    mobile = request.json.get("mobile")

    if not mobile:
        return jsonify(success=False, msg="Mobile required")

    user = User.query.filter_by(mobile=mobile).first()

    if not user:
        user = User(
            mobile=mobile,
            password=hash_password("default"),
            aadhaar_encrypted=encrypt_data("000000000000")
        )
        db.session.add(user)
        db.session.commit()
        db.session.add(UserProgress(user_id=user.id))
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
# CHATBOT API
# -----------------------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    user_msg = request.json.get("message", "").strip()

    if not user_msg:
        return jsonify({"reply": "Please say something."})

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

    db.session.add(ChatHistory(
        user_id=user_id,
        message=user_msg,
        reply=reply,
        language=lang
    ))

    if user_id:
        up = UserProgress.query.filter_by(user_id=user_id).first()
        if up:
            up.chatbot_usage_count += 1

    db.session.commit()

    return jsonify({"reply": reply})


# -----------------------------
# AUDIO CHAT (SIMPLIFIED - NO SPEECH LIB)
# -----------------------------
@app.route("/api/chat_audio", methods=["POST"])
def api_chat_audio():
    return jsonify({"error": "Speech feature removed for deployment stability"})


# -----------------------------
# KNOWLEDGE BASE
# -----------------------------
@app.route("/api/constitution", methods=["GET"])
def get_constitution_data():
    kb_items = KnowledgeBase.query.all()

    return jsonify({
        "success": True,
        "data": [
            {
                "id": k.id,
                "category": k.category,
                "title": k.title,
                "description": k.description
            }
            for k in kb_items
        ]
    })


@app.route("/api/search")
def search_knowledge_base():
    query = request.args.get("q", "").lower()

    if not query:
        return jsonify({"success": False})

    results = KnowledgeBase.query.filter(
        KnowledgeBase.title.ilike(f"%{query}%") |
        KnowledgeBase.description.ilike(f"%{query}%") |
        KnowledgeBase.keywords.ilike(f"%{query}%")
    ).all()

    return jsonify({
        "success": True,
        "data": [{"id": r.id, "title": r.title, "description": r.description} for r in results]
    })


# -----------------------------
# QUIZ
# -----------------------------
@app.route("/api/quiz/get")
def get_quiz():
    questions = QuizQuestion.query.all()

    if not questions:
        return jsonify({"success": False})

    selected = random.sample(questions, min(2, len(questions)))

    return jsonify({
        "success": True,
        "data": [
            {
                "id": q.id,
                "question": q.question,
                "options": q.get_options(),
                "type": q.type
            }
            for q in selected
        ]
    })


@app.route("/api/quiz/submit", methods=["POST"])
def submit_quiz():
    if "user_id" not in session:
        return jsonify({"success": False})

    answers = request.json.get("answers", {})

    score = 0
    feedback = []

    for qid, ans in answers.items():
        q = QuizQuestion.query.get(qid)

        if q:
            correct = q.correct_answer.strip().lower() == ans.strip().lower()
            if correct:
                score += 10

            feedback.append({
                "question_id": q.id,
                "correct": correct,
                "explanation": q.explanation
            })

    up = UserProgress.query.filter_by(user_id=session["user_id"]).first()
    if up:
        up.quiz_score += score
        up.topics_completed += 1
        db.session.commit()

    return jsonify({"success": True, "score": score, "feedback": feedback})


# -----------------------------
# PROGRESS
# -----------------------------
@app.route("/api/progress")
def get_progress():
    if "user_id" not in session:
        return jsonify({"success": False})

    up = UserProgress.query.filter_by(user_id=session["user_id"]).first()

    if not up:
        return jsonify({"success": False})

    return jsonify({
        "success": True,
        "articles_viewed": up.articles_viewed,
        "topics_completed": up.topics_completed,
        "chatbot_usage_count": up.chatbot_usage_count,
        "quiz_score": up.quiz_score
    })


# -----------------------------
# RUN (RENDER USES GUNICORN)
# -----------------------------
if __name__ == "__main__":
    app.run()