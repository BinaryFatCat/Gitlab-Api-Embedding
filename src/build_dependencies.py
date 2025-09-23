import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path

OPERATIONS_FILE = Path("outputs/operations.json")
EMBEDDINGS_FILE = Path("outputs/embeddings_qwen3.npy")
OUTPUT_FILE = Path("outputs/dependencies_qwen3.json")

THRESHOLD = 0.75

def build_dependencies():
    with open(OPERATIONS_FILE, "r", encoding="utf-8") as f:
        operations = json.load(f)
    embeddings = np.load(EMBEDDINGS_FILE)

    sim_matrix = cosine_similarity(embeddings)
    dependencies = {}

    for i, op in enumerate(operations):
        related = []
        for j, score in enumerate(sim_matrix[i]):
            if i != j and score >= THRESHOLD:
                related.append({
                    "operationId": operations[j]["operationId"],
                    "score": float(score)
                })
        dependencies[op["operationId"]] = related

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(dependencies, f, indent=2)

    print(f"✅ Built dependencies for {len(operations)} operations")

if __name__ == "__main__":
    build_dependencies()