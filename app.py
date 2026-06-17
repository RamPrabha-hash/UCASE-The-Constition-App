import os
import random
from datetime import datetime

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

from models import db, User, ChatHistory, UserProgress, KnowledgeBase, QuizQuestion
from security import encrypt_data, hash_password, validate_aadhaar_format
from nlp_engine import nlp, detect_language

# -----------------------------
# APP CONFIG
# -----------------------------
app = Flask(__name__)
app.secret_key = "ucase_super_secret_key"

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///ucase.db"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# -----------------------------
# TEMP OTP STORE
# -----------------------------
otp_store = {}

def generate_otp():
    return str(random.randint(100000, 999999))

# -----------------------------
# FRONTEND ROUTES
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
# AUTH APIs
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
        return jsonify(success=False, msg="Missing required fields")

    if not validate_aadhaar_format(aadhaar):
        return jsonify(success=False, msg="Invalid Aadhaar format")

    if User.query.filter_by(mobile=mobile).first():
        return jsonify(success=False, msg="User already exists")

    user = User(
        mobile=mobile,
        password=hash_password(password),
        aadhaar_encrypted=encrypt_data(aadhaar),
        age=age,
        address=address
    )

    db.session.add(user)
    db.session.commit()

    progress = UserProgress(user_id=user.id)
    db.session.add(progress)
    db.session.commit()

    return jsonify(success=True, msg="Registered successfully")

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

    print(f"OTP for {mobile}: {otp}")  # for testing only

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
            return jsonify(success=True, msg="Login successful")

    return jsonify(success=False, msg="Invalid OTP")

# -----------------------------
# CHAT API (NLP)
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

    state["stage"] = "responding"
    session.modified = True

    db.session.add(ChatHistory(
        user_id=user_id,
        message=user_msg,
        reply=reply,
        language=lang
    ))

    if user_id:
        prog = UserProgress.query.filter_by(user_id=user_id).first()
        if prog:
            prog.chatbot_usage_count += 1

    db.session.commit()

    return jsonify({"reply": reply})

# -----------------------------
# KNOWLEDGE BASE
# -----------------------------
@app.route("/api/constitution", methods=["GET"])
def get_constitution_data():
    items = KnowledgeBase.query.all()

    return jsonify({
        "success": True,
        "data": [
            {
                "id": i.id,
                "category": i.category,
                "title": i.title,
                "description": i.description
            } for i in items
        ]
    })

@app.route("/api/search")
def search():
    q = request.args.get("q", "").lower()

    if not q:
        return jsonify(success=False, msg="Query required")

    results = KnowledgeBase.query.filter(
        (KnowledgeBase.title.ilike(f"%{q}%")) |
        (KnowledgeBase.description.ilike(f"%{q}%")) |
        (KnowledgeBase.keywords.ilike(f"%{q}%"))
    ).all()

    user_id = session.get("user_id")
    if user_id:
        prog = UserProgress.query.filter_by(user_id=user_id).first()
        if prog:
            prog.articles_viewed += 1
            db.session.commit()

    return jsonify({
        "success": True,
        "data": [
            {"id": r.id, "title": r.title, "description": r.description}
            for r in results
        ]
    })

# -----------------------------
# QUIZ SYSTEM
# -----------------------------
@app.route("/api/quiz/get")
def get_quiz():
    qs = QuizQuestion.query.all()

    if not qs:
        return jsonify(success=False, msg="No quizzes")

    selected = random.sample(qs, min(2, len(qs)))

    return jsonify({
        "success": True,
        "data": [
            {
                "id": q.id,
                "question": q.question,
                "options": q.get_options(),
                "type": q.type
            } for q in selected
        ]
    })

@app.route("/api/quiz/submit", methods=["POST"])
def submit_quiz():
    if "user_id" not in session:
        return jsonify(success=False, msg="Login required")

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

    prog = UserProgress.query.filter_by(user_id=session["user_id"]).first()
    if prog:
        prog.quiz_score += score
        prog.topics_completed += 1
        db.session.commit()

    return jsonify({
        "success": True,
        "score_earned": score,
        "feedback": feedback
    })

# -----------------------------
# PROGRESS
# -----------------------------
@app.route("/api/progress")
def progress():
    if "user_id" not in session:
        return jsonify(success=False, msg="Not logged in")

    p = UserProgress.query.filter_by(user_id=session["user_id"]).first()

    if not p:
        return jsonify(success=False, msg="No data")

    return jsonify({
        "success": True,
        "articles_viewed": p.articles_viewed,
        "topics_completed": p.topics_completed,
        "chatbot_usage_count": p.chatbot_usage_count,
        "quiz_score": p.quiz_score
    })

# -----------------------------
# MAIN (RENDER ENTRY)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))