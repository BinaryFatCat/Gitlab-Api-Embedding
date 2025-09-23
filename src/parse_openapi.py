import yaml
import json
from pathlib import Path

INPUT_FILE = Path("data/openapi.yaml")
OUTPUT_FILE = Path("outputs/operations.json")

def extract_operations():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    operations = []
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch", "head"}:
                continue
            operations.append({
                "operationId": op.get("operationId"),
                "method": method.upper(),
                "path": path,
                "summary": op.get("summary", ""),
                "description": op.get("description", ""),
                "tags": op.get("tags", []),
                "full_text": f"{op.get('summary', '')}. {op.get('description', '')}".strip()
            })

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(operations, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    extract_operations()