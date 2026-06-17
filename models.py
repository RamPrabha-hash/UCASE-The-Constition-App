from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    aadhaar_encrypted = db.Column(db.Text, nullable=False)
    address = db.Column(db.Text, nullable=True)
    age = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    chat_history = db.relationship('ChatHistory', backref='user', lazy=True)
    progress = db.relationship('UserProgress', backref='user', uselist=False, lazy=True)

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Allow anonymous interactions initially
    session_id = db.Column(db.String(255), nullable=True) # Tie anonymous chats to session
    message = db.Column(db.Text, nullable=False)
    reply = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(20), default="english")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    articles_viewed = db.Column(db.Integer, default=0)
    topics_completed = db.Column(db.Integer, default=0)
    chatbot_usage_count = db.Column(db.Integer, default=0)
    quiz_score = db.Column(db.Integer, default=0)

class KnowledgeBase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False) # e.g., 'Article', 'Fundamental Right', 'Law'
    title = db.Column(db.String(255), nullable=False) # e.g., 'Article 21' or 'POSH Act 2013'
    description = db.Column(db.Text, nullable=False)
    keywords = db.Column(db.Text, nullable=True) # JSON array or comma separated

class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False) # JSON array: ["A", "B", "C", "D"]
    correct_answer = db.Column(db.String(255), nullable=False)
    explanation = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), default="MCQ") # 'MCQ' or 'True/False'

    def get_options(self):
        return json.loads(self.options) if self.options else []
