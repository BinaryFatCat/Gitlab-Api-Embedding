import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path

PARAM_META_FILE = Path("outputs/param_description_embeddings.json")
EMBEDDING_FILE = Path("outputs/param_description_embeddings.npy")
OUTPUT_FILE = Path("outputs/interface_parameter_dependencies.json")

SIMILARITY_THRESHOLD = 0.75

def main():
    with open(PARAM_META_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)

    embeddings = np.load(EMBEDDING_FILE)
    sim_matrix = cosine_similarity(embeddings)

    results = []

    for i, m1 in enumerate(meta):
        for j, m2 in enumerate(meta):
            if i >= j:
                continue
            if m1["direction"] != "response" or m2["direction"] != "input":
                continue
            score = float(sim_matrix[i][j])
            if score >= SIMILARITY_THRESHOLD:
                results.append({
                    "from_operationId": m1["operationId"],
                    "from_param_name": m1["param_name"],
                    "from_description": m1["description"],
                    "to_operationId": m2["operationId"],
                    "to_param_name": m2["param_name"],
                    "to_description": m2["description"],
                    "similarity_score": score,
                    "direction": "response → input"
                })

    results = sorted(results, key=lambda x: x["similarity_score"], reverse=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ 接口参数依赖分析完成，共 {len(results)} 条依赖关系")
    print(f"📁 结果保存在: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()