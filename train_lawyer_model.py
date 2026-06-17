import os
import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

def train_lawyer_recommender():
    dataset_path = "Lawyers.xlsx"
    if not os.path.exists(dataset_path):
        print(f"Dataset {dataset_path} not found.")
        return

    df = pd.read_excel(dataset_path)
    
    # Fill any empty fields
    df.fillna('', inplace=True)
    
    # We create a combined feature text to represent the lawyer's profile for the NLP model.
    # Ex: "Chennai Criminal" or "Coimbatore Civil"
    # We can also add extra weights to experience, but tf-idf handles text search best.
    df['combined_features'] = df['Location'].astype(str) + " " + df['Practice Area'].astype(str)
    
    # Initialize TF-IDF Vectorizer
    vectorizer = TfidfVectorizer(lowercase=True)
    tfidf_matrix = vectorizer.fit_transform(df['combined_features'])
    
    # Train Nearest Neighbors
    # We use cosine metric to find the perfect semantic text match for location + issue
    knn = NearestNeighbors(n_neighbors=5, metric='cosine')
    knn.fit(tfidf_matrix)
    
    os.makedirs("ai", exist_ok=True)
    
    with open("ai/lawyer_recommender.pkl", "wb") as f:
        pickle.dump({
            "vectorizer": vectorizer,
            "knn_model": knn,
            "dataframe": df
        }, f)
        
    print("Lawyer Recommendation Model trained and saved to ai/lawyer_recommender.pkl successfully!")

if __name__ == "__main__":
    train_lawyer_recommender()
