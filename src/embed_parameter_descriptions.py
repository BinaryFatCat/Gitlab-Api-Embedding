import json
import numpy as np
from pathlib import Path
from transformers import AutoTokenizer, AutoModel
import torch

MODEL_PATH = "models/Qwen3-Embedding-06B"
INPUT_FILE = Path("outputs/operation_parameters.json")
OUTPUT_EMBEDDING = Path("outputs/param_description_embeddings.npy")
OUTPUT_META = Path("outputs/param_description_embeddings.json")

@torch.inference_mode()
def get_embedding(texts):
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model = AutoModel.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model.eval()

    inputs = tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
    outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).cpu().numpy()

def embed_descriptions():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        operations = json.load(f)

    texts = []
    meta_info = []

    for op in operations:
        if op.get("direction") not in ("input", "response"):
            continue
        for param in op["parameters"]:
            desc = param.get("description", "").strip()
            if not desc:
                desc = param["name"]
            texts.append(desc)
            meta_info.append({
                "operationId": op["operationId"],
                "param_name": param["name"],
                "param_in": param["in"],
                "description": desc,
                "direction": op["direction"]
            })

    print(f"🧠 正在对 {len(texts)} 个参数描述生成 embedding...")
    embeddings = get_embedding(texts)

    np.save(OUTPUT_EMBEDDING, embeddings)
    with open(OUTPUT_META, "w", encoding="utf-8") as f:
        json.dump(meta_info, f, ensure_ascii=False, indent=2)

    print(f"✅ 完成！embedding 形状: {embeddings.shape}")

if __name__ == "__main__":
    embed_descriptions()