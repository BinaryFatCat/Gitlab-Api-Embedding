import json
import numpy as np
from pathlib import Path
from transformers import AutoTokenizer, AutoModel
import torch

MODEL_PATH = Path("models/Qwen3-Embedding-06B")
INPUT_FILE = Path("outputs/operations.json")
OUTPUT_FILE = Path("outputs/embeddings_qwen3.npy")

@torch.inference_mode()
def get_embedding(texts: list[str]) -> np.ndarray:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model = AutoModel.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model.eval()

    inputs = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    )
    outputs = model(**inputs)
    # 平均池化（Qwen3 默认无池化头）
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings.cpu().numpy()

def embed_operations():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        operations = json.load(f)

    texts = [op["full_text"] for op in operations]
    embeddings = get_embedding(texts)

    np.save(OUTPUT_FILE, embeddings)
    print(f"✅ Qwen3-Embedding 生成完成，形状：{embeddings.shape}")

if __name__ == "__main__":
    embed_operations()