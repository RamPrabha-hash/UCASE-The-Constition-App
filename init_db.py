import os
import pandas as pd
from app import app, db
from models import KnowledgeBase, QuizQuestion

def init_database():
    with app.app_context():
        # Clean existing mock data
        db.create_all()
        print("Database schema created.")

        seed_knowledge_base()
        seed_quiz_questions()
        
        print("Database initialization complete.")

def seed_knowledge_base():
    # Only seed if empty
    if KnowledgeBase.query.count() > 0:
        return

    csv_path = 'indian_legal_abuse_dataset_50000.csv'
    if os.path.exists(csv_path):
        print(f"Loading '{csv_path}' for knowledge base seeding...")
        df = pd.read_csv(csv_path).dropna(subset=['law'])
        unique_laws = df['law'].unique()
        
        for law in unique_laws:
            # We use a mocked description since the dataset only gives the law name
            desc = f"Information regarding {law} and its application in protecting individual rights."
            kb = KnowledgeBase(
                category="Criminal Law" if "IPC" in str(law) else "Civil Law / Domestic",
                title=str(law),
                description=desc,
                keywords=str(law).lower()
            )
            db.session.add(kb)
        db.session.commit()
    
    # Synthetically add some Constitution articles to fulfill the requirement
    articles = [
        {"cat": "Fundamental Right", "title": "Article 14", "desc": "Equality before the law."},
        {"cat": "Fundamental Right", "title": "Article 15", "desc": "Prohibition of discrimination on grounds of religion, race, caste, sex or place of birth."},
        {"cat": "Fundamental Right", "title": "Article 19", "desc": "Protection of certain rights regarding freedom of speech, etc."},
        {"cat": "Fundamental Right", "title": "Article 21", "desc": "Protection of life and personal liberty."}
    ]
    for art in articles:
        kb = KnowledgeBase(category=art['cat'], title=art['title'], description=art['desc'], keywords=art['title'].lower())
        db.session.add(kb)
    db.session.commit()

def seed_quiz_questions():
    if QuizQuestion.query.count() > 0:
        return
        
    print("Seeding some basic quiz questions...")
    q1 = QuizQuestion(
        question="Which article guarantees Equality before the law?",
        options='["Article 14", "Article 21", "Article 19", "Article 15"]',
        correct_answer="Article 14",
        explanation="Article 14 ensures equality before the law.",
        type="MCQ"
    )
    q2 = QuizQuestion(
        question="Which act specifically provides protection to women in households?",
        options='["IT Act Section 67", "Domestic Violence Act 2005", "POSH Act", "IPC 354"]',
        correct_answer="Domestic Violence Act 2005",
        explanation="The Domestic Violence Act 2005 protects women from abuse in a domestic setting.",
        type="MCQ"
    )
    db.session.add_all([q1, q2])
    db.session.commit()

if __name__ == '__main__':
    init_database()
