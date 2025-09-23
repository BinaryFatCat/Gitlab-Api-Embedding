import json
import numpy as np
from pathlib import Path
from collections import Counter

def load(file: Path):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def tag_purity(dep_file: Path, ops_file: Path):
    dep = load(dep_file)
    ops = load(ops_file)
    # 建立 id → tags 映射
    id2tags = {op["operationId"]: set(op["tags"]) for op in ops}

    purity = []
    for op, neighbors in dep.items():
        if not neighbors:
            continue
        op_tags = id2tags[op]
        # 邻居所有标签（去重）
        neigh_tags = set(t for n in neighbors for t in id2tags[n["operationId"]])
        if not neigh_tags:
            continue
        purity.append(len(op_tags & neigh_tags) / len(neigh_tags))
    return np.mean(purity) if purity else 0.0

def main():
    ops_file = Path("outputs/operations.json")
    mini_dep = Path("outputs/dependencies.json")
    qwen_dep = Path("outputs/dependencies_qwen3.json")

    mini_pur = tag_purity(mini_dep, ops_file)
    qwen_pur = tag_purity(qwen_dep, ops_file)

    out = Path("outputs/tag_purity_result.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"MiniLM 模块纯度：{mini_pur:.3f}\n")
        f.write(f"Qwen3  模块纯度：{qwen_pur:.3f}\n")
        if qwen_pur > mini_pur:
            f.write("→ Qwen3 更能把同模块 API 聚到一起 ✅\n")
        else:
            f.write("→ MiniLM 更优 ✅\n")
    print(f"✅ 结果已保存至：{out}")
    print(f"MiniLM 模块纯度：{mini_pur:.3f}")
    print(f"Qwen3  模块纯度：{qwen_pur:.3f}")

if __name__ == "__main__":
    main()