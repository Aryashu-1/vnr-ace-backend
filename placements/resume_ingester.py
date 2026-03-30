import os
import faiss
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def get_embedding(text: str) -> list:
    embedding = model.encode(text)
    return embedding.tolist()

import fitz
import spacy

def extract_text_from_pdf(path):
    doc = fitz.open(path)
    text = " ".join(page.get_text() for page in doc)
    
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text)
    
    filtered_tokens = [token.lemma_ for token in doc if token.is_alpha]
    return " ".join(filtered_tokens)

def chunk_text(text, size=800):
    return [text[i:i+size] for i in range(0, len(text), size)]

EMBEDDING_DIM = 384
CHUNK_SIZE = 800
FAISS_PATH = "faiss_index/"


os.makedirs(FAISS_PATH, exist_ok=True)

index = faiss.IndexFlatIP(EMBEDDING_DIM)
metadata = []

resume_folder = "resumes/"

for resume_file in os.listdir(resume_folder):
    if not resume_file.endswith(".pdf"):
        continue

    resume_id = resume_file
    text = extract_text_from_pdf(os.path.join(resume_folder, resume_file))
    chunks = chunk_text(text, CHUNK_SIZE)

    for chunk_id, chunk in enumerate(chunks):
        embedding = np.array(get_embedding(chunk)).astype("float32")
        faiss.normalize_L2(embedding.reshape(1, -1))

        index.add(embedding.reshape(1, -1))

        metadata.append({
            "resume_id": resume_id,
            "chunk_id": chunk_id,
            "text": chunk
        })

    print(f"✅ Ingested {resume_id}")

faiss.write_index(index, f"{FAISS_PATH}/index.faiss")
with open(f"{FAISS_PATH}/metadata.pkl", "wb") as f:
    pickle.dump(metadata, f)
