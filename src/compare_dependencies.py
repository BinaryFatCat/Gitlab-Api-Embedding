import json
import numpy as np
from pathlib import Path
from collections import Counter

def load_dep(file: Path):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def stats(name, dep):
    neigh = [len(v) for v in dep.values()]
    return {
        "model": name,
        "avg_neighbors": np.mean(neigh),
        "median_neighbors": np.median(neigh),
        "total_edges": sum(neigh),
        "isolates": sum(1 for n in neigh if n == 0),
    }

def main():
    mini = load_dep(Path("outputs/dependencies.json"))
    qwen = load_dep(Path("outputs/dependencies_qwen3.json"))

    print("{:<10} {:>8} {:>8} {:>10} {:>8}".format(
        "模型", "avg_n", "med_n", "edges", "isolates"))
    for s in [stats("MiniLM", mini), stats("Qwen3", qwen)]:
        print("{model:<10} {avg_neighbors:8.2f} {median_neighbors:8.0f} "
              "{total_edges:10.0f} {isolates:8.0f}".format(**s))

    # 同时写入结果文件
    out_file = Path("outputs/compare_dependencies_result.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("{:<10} {:>8} {:>8} {:>10} {:>8}\n".format(
            "模型", "avg_n", "med_n", "edges", "isolates"))
        for s in [stats("MiniLM", mini), stats("Qwen3", qwen)]:
            f.write("{model:<10} {avg_neighbors:8.2f} {median_neighbors:8.0f} "
                    "{total_edges:10.0f} {isolates:8.0f}\n".format(**s))
    print(f"✅ 结果已保存至：{out_file}")

if __name__ == "__main__":
    main()