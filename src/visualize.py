import json
import matplotlib.pyplot as plt
import networkx as nx
from pathlib import Path

DEP_FILE = Path("outputs/dependencies_qwen3.json")
OUTPUT_IMAGE = Path("outputs/dependency_graph_qwen3.png")

def visualize():
    with open(DEP_FILE, "r", encoding="utf-8") as f:
        deps = json.load(f)

    G = nx.DiGraph()
    for op, related in deps.items():
        G.add_node(op)
        for r in related:
            G.add_edge(op, r["operationId"])

    plt.figure(figsize=(20, 20))
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    nx.draw(G, pos, with_labels=True, node_size=100, font_size=4, alpha=0.7)
    plt.title("GitLab API Operation Dependency Graph (Semantic Similarity)")
    plt.savefig(OUTPUT_IMAGE, dpi=300)
    print(f"✅ Saved dependency graph to {OUTPUT_IMAGE}")

if __name__ == "__main__":
    visualize()