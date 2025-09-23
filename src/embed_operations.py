import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

INPUT_FILE = Path("outputs/operations.json")
OUTPUT_FILE = Path("outputs/embeddings.npy")

model = SentenceTransformer("models/all-MiniLM-L6-v2")

def embed_operations():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        operations = json.load(f)

    texts = [op["full_text"] for op in operations]
    embeddings = model.encode(texts, show_progress_bar=True)

    np.save(OUTPUT_FILE, embeddings)
    print(f"✅ Saved embeddings shape: {embeddings.shape}")

if __name__ == "__main__":
    embed_operations()