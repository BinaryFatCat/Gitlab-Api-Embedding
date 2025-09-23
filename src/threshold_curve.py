import json
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
import argparse

OPS_FILE   = Path("outputs/operations.json")
EMB_FILE   = Path("outputs/embeddings_qwen3.npy")   # 用 Qwen3 向量
OUT_FILE   = Path("outputs/threshold_curve_qwen3.txt")

def load(file: Path):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def purity_at_threshold(threshold: float, dep: dict, ops: list) -> float:
    id2tags = {op["operationId"]: set(op["tags"]) for op in ops}
    purity = []
    for op, neighbors in dep.items():
        neigh = [n for n in neighbors if n["score"] >= threshold]
        if not neigh:
            continue
        op_tags = id2tags[op]
        neigh_tags = set(t for n in neigh for t in id2tags[n["operationId"]])
        purity.append(len(op_tags & neigh_tags) / max(len(neigh_tags), 1))
    return np.mean(purity) if purity else 0.0

def main():
    ops = load(OPS_FILE)
    embeddings = np.load(EMB_FILE)
    sim_matrix = cosine_similarity(embeddings)

    # 预生成全量邻居（只算一次）
    dep = {}
    for i, op in enumerate(ops):
        dep[op["operationId"]] = [
            {"operationId": ops[j]["operationId"], "score": float(sim_matrix[i][j])}
            for j in range(len(ops)) if i != j
        ]

    thresholds = np.arange(0.65, 0.81, 0.01)
    results = []
    for t in thresholds:
        pur = purity_at_threshold(t, dep, ops)
        neigh_cnt = [len([n for n in v if n["score"] >= t]) for v in dep.values()]
        avg_n = np.mean(neigh_cnt)
        total_e = sum(neigh_cnt)
        isolates = sum(1 for n in neigh_cnt if n == 0)
        results.append((t, pur, avg_n, total_e, isolates))
        print(f"thresh={t:.2f} 纯度={pur:.3f} avg_n={avg_n:.2f} edges={total_e} isolates={isolates}")

    # 写入文件
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write("thresh purity avg_n edges isolates\n")
        for t, pur, avg_n, total_e, isolates in results:
            f.write(f"{t:.2f} {pur:.3f} {avg_n:.2f} {total_e} {isolates}\n")
    print(f"✅ 曲线已保存：{OUT_FILE}")

if __name__ == "__main__":
    main()