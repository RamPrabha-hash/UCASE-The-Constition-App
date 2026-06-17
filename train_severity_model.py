import os
import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline

# Synthetic dataset for Severity / Legal Need Classification
# Label 1: Severe / Wants Legal Action
# Label 0: Low Severity / Just Venting / Emotionally distressed but not legal

data = [
    # Label 1: Severe cases
    ("It is getting very violent, I want to take legal action.", 1),
    ("Yes, I think I need a lawyer for this.", 1),
    ("They are threatening me physically.", 1),
    ("I want to file an FIR.", 1),
    ("Please help me find a good lawyer.", 1),
    ("I cannot take this abuse anymore, I need police help.", 1),
    ("Yes please connect me to a lawyer.", 1),
    ("It's an emergency, I need legal protection.", 1),
    ("This is a severe cybercrime and I want to report it.", 1),
    ("Someone is stalking me and I fear for my life.", 1),
    ("I want to complain against my husband for domestic violence.", 1),
    ("I need to proceed legally.", 1),
    
    # Label 1: Tamil/Hindi/Tanglish mapping equivalents
    ("Na legal ah proceed panna virumburen.", 1),
    ("Mujhe lawyer chahiye.", 1),
    ("Enakku police help thevai.", 1),
    ("Haan, mujhe kanooni madad ki zarurat hai.", 1),
    ("Lawyer ta enaku pesanumnu aasa.", 1),
    
    # Label 0: Low severity / Emotional
    ("I just wanted to talk to someone about my stress.", 0),
    ("No, I don't want a lawyer right now.", 0),
    ("It's fine, I'll manage.", 0),
    ("I'm just feeling a bit depressed.", 0),
    ("I don't think it's that serious.", 0),
    ("We just had a verbal argument, that's it.", 0),
    ("No I don't want to involve the police.", 0),
    ("Just need some advice to calm down.", 0),
    
    # Label 0: Tamil/Hindi/Tanglish equivalents
    ("Illa venam, nane paathukkuren.", 0),
    ("Nahi, mujhe lawyer nahi chahiye.", 0),
    ("Konjam manasu kastama iruku avlodhan.", 0),
    ("Koi baat nahi, mai theek hu.", 0),
    ("Venda, police ellam theva illa.", 0)
]

df = pd.DataFrame(data, columns=['text', 'label'])

print("Training Severity Assessment Model...")

pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
    ('clf', SVC(kernel='linear', probability=True))
])

pipeline.fit(df['text'], df['label'])

# Ensure AI directory exists
os.makedirs("ai", exist_ok=True)

with open("ai/severity_model.pkl", "wb") as f:
    pickle.dump(pipeline, f)

print("Severity Model saved to ai/severity_model.pkl successfully!")
