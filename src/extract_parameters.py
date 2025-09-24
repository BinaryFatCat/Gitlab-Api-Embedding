import prance
import json
from pathlib import Path

INPUT_FILE = Path("data/openapi.yaml")
OUTPUT_FILE = Path("outputs/operation_parameters.json")

def extract_parameters():
    # ❶ 让 prance 帮你把 $ref 全部解析成完整定义
    parser = prance.ResolvingParser(str(INPUT_FILE), backend='openapi-spec-validator', strict=False)
    spec = parser.specification   

    result = []

    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch", "head"}:
                continue

            operation_id = op.get("operationId")
            summary = op.get("summary", "")
            description = op.get("description", "")

            param_list = []

            # ❷ 路径参数
            for param in op.get("parameters", []):
                param_list.append({
                    "name": param.get("name"),
                    "in": param.get("in"),
                    "description": param.get("description", ""),
                    "schema": param.get("schema", {}),
                    "required": param.get("required", False)
                })

            # ❸ 请求体参数
            if "requestBody" in op:
                content = op["requestBody"].get("content", {})
                for content_type, schema_obj in content.items():
                    schema = schema_obj.get("schema", {})
                    if "properties" in schema:
                        for prop_name, prop_def in schema["properties"].items():
                            param_list.append({
                                "name": prop_name,
                                "in": "body",
                                "description": prop_def.get("description", ""),
                                "schema": prop_def,
                                "required": prop_name in schema.get("required", [])
                            })

            result.append({
                "operationId": operation_id,
                "method": method.upper(),
                "path": path,
                "summary": summary,
                "description": description,
                "parameters": param_list
            })

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 提取完成，共 {len(result)} 个接口，参数保存在 {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_parameters()