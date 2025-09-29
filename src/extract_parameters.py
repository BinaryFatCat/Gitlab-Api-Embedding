import prance
import json
from pathlib import Path
from datetime import datetime

INPUT_FILE = Path("data/openapi.yaml")
OUTPUT_FILE = Path("outputs/operation_parameters.json")

def flatten_schema(schema: dict, required_fields: list) -> list:
    params = []
    if not schema:
        return params

    if schema.get("type") == "object" and "properties" in schema:
        for prop_name, prop_def in schema["properties"].items():
            params.append({
                "name": prop_name,
                "in": "body",
                "description": prop_def.get("description", ""),
                "schema": prop_def,
                "required": prop_name in schema.get("required", []),
                "direction": "response"   
            })
        return params

    if schema.get("type") == "array" and "items" in schema:
        params.extend(flatten_schema(schema["items"], []))
        return params

    for key in ("allOf", "oneOf", "anyOf"):
        if key in schema:
            for sub in schema[key]:
                params.extend(flatten_schema(sub, required_fields))
            return params
    return params


def extract_parameters():
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

            # 提取 path 参数
            for param in op.get("parameters", []):
                param_list.append({
                    "name": param.get("name"),
                    "in": param.get("in"),
                    "description": param.get("description", ""),
                    "schema": param.get("schema", {}),
                    "required": param.get("required", False),
                    "direction": "input"
                })

            # 提取 body 参数
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
                                "required": prop_name in schema.get("required", []),
                                "direction": "input"
                            })

            # 提取 response 参数
            if "responses" in op:
                for status, resp_obj in op["responses"].items():
                    content = resp_obj.get("content", {})
                    for content_type, schema_obj in content.items():
                        schema = schema_obj.get("schema", {})
                        flat = flatten_schema(schema, [])
                        param_list.extend(flat)


            inp_params  = [p for p in param_list if p.get("direction") == "input"]
            resp_params = [p for p in param_list if p.get("direction") == "response"]

            if inp_params:
                result.append({
                    "operationId": operation_id,
                    "method": method.upper(),
                    "path": path,
                    "summary": summary,
                    "description": description,
                    "direction": "input",
                    "parameters": inp_params
                })
            if resp_params:
                result.append({
                    "operationId": operation_id,
                    "method": method.upper(),
                    "path": path,
                    "summary": summary,
                    "description": description,
                    "direction": "response",
                    "parameters": resp_params
                })

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=lambda o: o.isoformat() if isinstance(o, datetime) else str(o))
    print(f"✅ 提取完成，共 {len(result)} 条记录，保存在 {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_parameters()