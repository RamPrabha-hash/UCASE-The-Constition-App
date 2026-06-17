import pandas as pd
import torch
import os
from sklearn.model_selection import train_test_split
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from torch.utils.data import Dataset

# 1. Prepare Dataset Class
class AbuseDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

def train_bert_model(csv_path="indian_legal_abuse_dataset_50000.csv", model_dir="ai/bert_abuse_model_tf"):
    print("Loading Dataset...")
    if not os.path.exists(csv_path):
        print(f"Error: Could not find {csv_path}")
        return

    # Load data
    df = pd.read_csv(csv_path).dropna(subset=['text', 'abuse_type'])
    
    # We will train the model to classify the 'abuse_type' based on 'text'
    # Create label mapping
    unique_labels = df['abuse_type'].unique()
    label2id = {label: i for i, label in enumerate(unique_labels)}
    id2label = {i: label for label, i in label2id.items()}
    
    df['label'] = df['abuse_type'].map(label2id)
    
    texts = df['text'].tolist()
    labels = df['label'].tolist()
    
    # Split
    train_texts, val_texts, train_labels, val_labels = train_test_split(texts, labels, test_size=0.1)

    print("Loading Multilingual Tokenizer...")
    # Multilingual BERT 
    model_name = "bert-base-multilingual-cased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    train_encodings = tokenizer(train_texts, truncation=True, padding=True, max_length=128)
    val_encodings = tokenizer(val_texts, truncation=True, padding=True, max_length=128)
    
    train_dataset = AbuseDataset(train_encodings, train_labels)
    val_dataset = AbuseDataset(val_encodings, val_labels)

    print("Initializing Model...")
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, 
        num_labels=len(unique_labels),
        id2label=id2label,
        label2id=label2id
    )

    training_args = TrainingArguments(
        output_dir='./results',
        num_train_epochs=3,              # Increase for better accuracy
        per_device_train_batch_size=16,
        per_device_eval_batch_size=64,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir='./logs',
        logging_steps=10,
        evaluation_strategy="epoch",
        save_strategy="epoch"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset
    )

    print("Starting Training Loop... (This may take several hours on CPU)")
    trainer.train()

    print(f"Saving Fine-Tuned Model to {model_dir}...")
    model.save_pretrained(model_dir)
    tokenizer.save_pretrained("ai/bert_abuse_tokenizer_tf")
    print("Training Complete!")

if __name__ == "__main__":
    train_bert_model()
