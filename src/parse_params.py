import yaml
import traceback
from typing import Dict, List, Tuple, Any, Optional
import os


# GitLab API 常见字段映射表
FIELD_MAPPING = {
    "project_id": "id",
    "user_id": "id",
    "group_id": "id",
    "badge_id": "id",
    "alert_iid": "id",
    "cluster_id": "id",
    "import_id": "id",
    "job_id": "id",
    "branch": "name",
    "key": "id"
}

# 资源类型 → 业务标识映射表
RESOURCE_BUSINESS_TAG = {
    "projects": "project",
    "jobs": "job",
    "broadcast_messages": "broadcast",
    "groups": "group",
    "badges": "badge",
    "clusters": "cluster",
    "applications": "application",
    "batched_background_migrations": "batched_bg_migration"
}

# 路径参数名 → 业务标识映射
PATH_PARAM_BUSINESS_TAG = {
    "batched_background_migrations": "batched_bg_migration",
    "broadcast_messages": "broadcast",
    "jobs": "job",
    "projects": "project"
}


def load_openapi_dict(file_path: str) -> Dict[str, Any]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            openapi_dict = yaml.safe_load(f)
        # 验证 OpenAPI 基本结构
        required_keys = ["openapi", "paths", "components"]
        for key in required_keys:
            if key not in openapi_dict:
                raise ValueError(f"OpenAPI 文件缺失必要字段: {key}")
        print(f"✅ 成功加载 OpenAPI 文件，包含:")
        print(f"  - paths 数量: {len(openapi_dict.get('paths', {}))} 个")
        print(f"  - 公共 schema 数量: {len(openapi_dict.get('components', {}).get('schemas', {}))} 个")
        return openapi_dict
    except Exception as e:
        print(f"❌ 加载 OpenAPI 文件失败: {e}")
        raise


def _get_response_schema_from_dict(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:

    json_content_types = [
        "application/json",
        "application/vnd.gitlab+json",
        "application/json; charset=utf-8"
    ]

    # 检查是否有 content
    content = response.get("content", {})
    if not content:
        print("  ❌ 响应无 content 定义")
        return None

    # 查找目标 JSON 类型
    target_schema = None
    target_type = None
    for content_type in json_content_types:
        if content_type in content:
            target_type = content_type
            target_schema = content[content_type].get("schema")
            break

    if not target_schema:
        print(f"  ❌ 无可用 JSON schema（content 类型: {list(content.keys())}）")
        return None

    # 验证 schema 是字典
    if not isinstance(target_schema, dict):
        print(f"  ❌ schema 不是字典类型（实际类型: {type(target_schema)}）")
        return None

    print(f"  ✅ 提取 {target_type} schema，包含字段: {list(target_schema.keys())[:5]}...")
    return target_schema


def extract_operations_from_dict(openapi_dict: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """从 OpenAPI 字典中提取接口操作信息（优化业务标识提取逻辑）"""
    operations: Dict[str, Dict[str, Any]] = {}
    paths = openapi_dict.get("paths", {})
    methods = ["get", "post", "put", "delete", "patch", "head", "options"]

    for path, path_config in paths.items():
        # 提取当前接口的业务场景标识
        business_tags = []
        for resource, tag in RESOURCE_BUSINESS_TAG.items():
            if resource in path:
                business_tags.append(tag)
        # 保留更具体的子资源标识
        business_tags = list(set(business_tags))
        if len(business_tags) > 1:
            # 排除通用父资源
            business_tags = [tag for tag in business_tags if tag not in ["project", "group"]]
        # 若仍无标识，尝试从路径最后一段提取资源
        if not business_tags:
            path_segments = [seg for seg in path.split("/") if seg and not seg.startswith("{")]
            if path_segments:
                last_segment = path_segments[-1]
                business_tags = [RESOURCE_BUSINESS_TAG.get(last_segment, last_segment)]

        for method in methods:
            if method not in path_config:
                continue

            op_config = path_config[method]
            op_id = f"{method.upper()} {path}"
            print(f"\n=== 处理接口: {op_id} ===")

            # 初始化操作数据
            operations[op_id] = {
                "op_id": op_id,
                "path": path,  
                "business_tags": business_tags,  # 接口的业务场景标识
                "input": {
                    "parameters": op_config.get("parameters", []),
                    "request_body": op_config.get("requestBody"),
                    "request_body_resolved": {},
                    "parameters_resolved": []
                },
                "output": None,
                "output_resolved": {},
                "raw_response": None
            }

            # 提取 2xx 响应的 schema
            responses = op_config.get("responses", {})
            response_found = False
            for status_code, resp_config in responses.items():
                if str(status_code).startswith("2"):
                    print(f"  处理响应（状态码: {status_code}）")
                    operations[op_id]["raw_response"] = resp_config
                    operations[op_id]["output"] = _get_response_schema_from_dict(resp_config)
                    response_found = True
                    break

            if not response_found:
                print("  ❌ 未找到 2xx 成功响应定义")

    print(f"\n✅ 共提取到 {len(operations)} 个接口操作")
    return operations


def resolve_ref_recursive(schema: Any, components: Dict[str, Any], indent: int = 0) -> Any:
    prefix = "  " * indent
    if not isinstance(schema, dict):
        return schema

    # 处理 $ref 引用
    if "$ref" in schema:
        ref_path = schema["$ref"].lstrip("#/")
        ref_parts = ref_path.split("/")
        if len(ref_parts) >= 2 and ref_parts[0] == "components" and ref_parts[1] == "schemas":
            ref_key = ref_parts[2]
            print(f"{prefix}🔍 解析引用: #/components/schemas/{ref_key}")
            ref_schema = components.get(ref_key, {})
            if not ref_schema:
                print(f"{prefix}❌ 未找到引用的 schema: {ref_key}")
                return schema
            # 递归解析引用的 schema
            return resolve_ref_recursive(ref_schema, components, indent + 1)

    # 处理数组类型
    if schema.get("type") == "array":
        print(f"{prefix}📋 解析数组类型，处理 items 引用")
        items = schema.get("items", {})
        if isinstance(items, dict):
            resolved_items = resolve_ref_recursive(items, components, indent + 1)
            schema["items"] = resolved_items
        return schema

    # 处理对象类型
    if schema.get("type") == "object":
        return schema

    # 其他类型直接返回
    return schema


def get_output_fields(op_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """提取出参字段并绑定业务标识（修复：补充字段级业务标识）"""
    output_fields: Dict[str, Dict[str, Any]] = {}
    output_resolved = op_data.get("output_resolved", {})
    components = op_data.get("_components", {})  # 公共 schema 组件
    upstream_business_tags = op_data.get("business_tags", [])  # 上游接口的业务标识
    op_path = op_data.get("path", "")  # 上游接口路径

    # 辅助函数：递归解析 schema 并提取字段
    def parse_schema(schema: Any, parent_business_tag: Optional[str] = None) -> None:
        # 解析引用
        if isinstance(schema, dict) and "$ref" in schema:
            ref_key = schema["$ref"].split("/")[-1]
            ref_schema = components.get(ref_key, {})
            if ref_schema:
                print(f"    🔍 递归解析引用对象: {ref_key}")
                # 从引用名推导字段标识
                ref_business_tag = None
                for tag in upstream_business_tags:
                    if tag in ref_key.lower():
                        ref_business_tag = tag
                        break
                parse_schema(ref_schema, ref_business_tag or parent_business_tag)
            return

        # 解析数组
        if isinstance(schema, dict) and schema.get("type") == "array":
            items = schema.get("items", {})
            if items:
                print(f"    🔍 解析数组元素")
                parse_schema(items, parent_business_tag)
            return

        # 解析对象
        if isinstance(schema, dict) and schema.get("type") == "object":
            properties = schema.get("properties", {})
            if not properties:
                print(f"    ⚠️ 对象 schema 无 properties 字段")
                return

            for prop_name, prop_details in properties.items():
                if not isinstance(prop_details, dict):
                    continue

                # 为出参字段绑定业务标识（优先级从高到低）
                field_business_tag = None
                # 字段名含业务前缀
                for resource, tag in RESOURCE_BUSINESS_TAG.items():
                    if f"{tag}_id" == prop_name or prop_name == tag:
                        field_business_tag = tag
                        break
                # 引用对象推导的标识
                if not field_business_tag and parent_business_tag:
                    field_business_tag = parent_business_tag
                # 上游接口的业务标识
                if not field_business_tag and upstream_business_tags:
                    field_business_tag = upstream_business_tags[0]

                # 保存字段信息
                output_fields[prop_name] = {
                    "type": prop_details.get("type"),
                    "example": prop_details.get("example"),
                    "description": prop_details.get("description"),
                    "business_tag": field_business_tag 
                }

            print(f"    ✅ 提取到 {len(properties)} 个字段")
            return

        # 其他类型不处理
        print(f"    ⚠️ 非对象/数组类型，跳过解析")

    # 开始解析出参 schema
    print(f"  🔍 开始解析出参结构")
    parse_schema(output_resolved)

    return output_fields

def resolve_all_refs(operations: Dict[str, Dict[str, Any]], openapi_dict: Dict[str, Any]) -> None:
    print("\n" + "="*50)
    print("开始解析引用关系（$ref）")
    print("="*50)

    # 加载公共组件 schema
    components = openapi_dict.get("components", {}).get("schemas", {})
    print(f"✅ 加载公共组件 schema 共 {len(components)} 个")

    for op_id, op_data in operations.items():
        print(f"\n=== 解析接口: {op_id} ===")

        # 解析出参引用
        if op_data["output"]:
            try:
                print("  解析出参引用...")
                resolved_output = resolve_ref_recursive(op_data["output"], components)
                op_data["output_resolved"] = resolved_output

                # 正确计算字段数量
                if isinstance(resolved_output, dict):
                    prop_count = 0
                    # 响应是数组类型 → 统计数组元素的 properties
                    if resolved_output.get("type") == "array":
                        items = resolved_output.get("items", {})
                        if isinstance(items, dict) and items.get("type") == "object":
                            prop_count = len(items.get("properties", {}))
                    # 响应是对象类型 → 直接统计自身的 properties
                    elif resolved_output.get("type") == "object":
                        prop_count = len(resolved_output.get("properties", {}))

                print(f"  ✅ 出参解析完成，包含 {prop_count} 个字段")
            except Exception as e:
                print(f"  ❌ 解析出参失败: {e}")
                op_data["output_resolved"] = {}
        else:
            print("  ⚠️  无出参 schema 可解析")
            op_data["output_resolved"] = {}

        # 解析请求体引用
        req_body = op_data["input"]["request_body"]
        if req_body:
            try:
                print("  解析请求体引用...")
                req_content = req_body.get("content", {})
                req_schema = None
                # 优先处理 JSON 类型的请求体
                for content_type in ["application/json", "application/vnd.gitlab+json"]:
                    if content_type in req_content:
                        req_schema = req_content[content_type].get("schema")
                        break
                # 递归解析请求体中的 $ref
                if req_schema and isinstance(req_schema, dict):
                    resolved_body = resolve_ref_recursive(req_schema, components)
                    op_data["input"]["request_body_resolved"] = resolved_body
                print("  ✅ 请求体解析完成")
            except Exception as e:
                print(f"  ❌ 解析请求体失败: {e}")
                op_data["input"]["request_body_resolved"] = {}

        # 解析参数引用
        resolved_params = []
        for param in op_data["input"]["parameters"]:
            try:
                if isinstance(param, dict) and "schema" in param:
                    param_schema = param["schema"]
                    if isinstance(param_schema, dict):
                        # 递归解析参数 schema 中的 $ref
                        resolved_schema = resolve_ref_recursive(param_schema, components)
                        param["schema"] = resolved_schema
                resolved_params.append(param)
            except Exception as e:
                print(f"  ❌ 解析参数失败: {e}")
                resolved_params.append(param)
        op_data["input"]["parameters_resolved"] = resolved_params

        # 缓存公共组件到接口数据中，供后续字段提取使用
        op_data["_components"] = components


def get_input_fields(op_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    input_fields: Dict[str, Dict[str, Any]] = {}
    op_path = op_data.get("path", "")  # 接口原始路径

    # 提取路径/查询参数
    for param in op_data["input"]["parameters_resolved"]:
        if not isinstance(param, dict):
            continue
        param_name = param.get("name")
        param_in = param.get("in")  # 参数位置（path/query）
        param_schema = param.get("schema", {})
        if not param_name or not isinstance(param_schema, dict):
            continue

        # 为路径参数绑定业务标识
        param_business_tag = None
        if param_in == "path":
            # 遍历路径中的资源，匹配参数对应的资源
            for resource, tag in PATH_PARAM_BUSINESS_TAG.items():
                if resource in op_path and f"/{resource}/" in op_path:
                    # 若参数在资源路径后，则绑定该资源的标识
                    param_business_tag = tag
                    break
            # 若未匹配，用接口的业务标识
            if not param_business_tag:
                param_business_tag = op_data["business_tags"][0] if op_data["business_tags"] else None

        input_fields[param_name] = {
            "type": param_schema.get("type"),
            "schema": param_schema,
            "source": param_in,  # 明确参数来源
            "business_tag": param_business_tag  # 入参字段的专属业务标识
        }

    # 提取请求体字段
    req_body = op_data["input"]["request_body_resolved"]
    if isinstance(req_body, dict) and req_body.get("type") == "object":
        properties = req_body.get("properties", {})
        for prop_name, prop_schema in properties.items():
            if isinstance(prop_schema, dict):
                # 请求体字段的业务标识：默认继承接口的业务标识
                req_business_tag = op_data["business_tags"][0] if op_data["business_tags"] else None
                input_fields[prop_name] = {
                    "type": prop_schema.get("type"),
                    "schema": prop_schema,
                    "source": "request_body",
                    "business_tag": req_business_tag  
                }

    return input_fields


def is_compatible(
    output_fields: Dict[str, Any], 
    input_fields: Dict[str, Any]
) -> bool:
    if not input_fields:
        return False  # 无入参的接口不匹配任何上游

    for field_name, input_spec in input_fields.items():
        # 字段名匹配
        matched_field = field_name
        if matched_field not in output_fields:
            matched_field = FIELD_MAPPING.get(field_name)
        if not matched_field or matched_field not in output_fields:
            print(f"    ❌ 字段名不匹配：下游 {field_name} 未在上游找到对应字段")
            return False

        # 提取上下游字段的详细信息
        output_spec = output_fields[matched_field]
        input_type = input_spec.get("type")
        output_type = output_spec.get("type")
        input_biz_tag = input_spec.get("business_tag")  # 下游入参字段的标识
        output_biz_tag = output_spec.get("business_tag")  # 上游出参字段的标识

        # 类型匹配
        if input_type and output_type:
            type_compatible = (
                input_type == output_type
                or (input_type in ["int", "integer"] and output_type == "number")
                or (input_type == "number" and output_type in ["int", "integer"])
            )
            if not type_compatible:
                print(f"    ❌ 类型不匹配：{input_type}（下游）≠ {output_type}（上游）")
                return False

        # 字段级业务标识校验
        # 若上下游任一字段无标识，视为语义不明，不匹配
        if not input_biz_tag or not output_biz_tag:
            print(f"    ❌ 业务标识缺失：上游 {matched_field}({output_biz_tag}) / 下游 {field_name}({input_biz_tag})")
            return False
        # 标识必须完全一致
        if input_biz_tag != output_biz_tag:
            print(f"    ❌ 业务标识不匹配：{input_biz_tag}（下游）≠ {output_biz_tag}（上游）")
            return False

        # 嵌套对象递归检查
        if output_type == "object" and input_type == "object":
            output_nested = output_spec.get("schema", {}).get("properties", {})
            input_nested = input_spec.get("schema", {}).get("properties", {})
            if not is_compatible(output_nested, input_nested):
                return False

    return True


def save_dependency_results(dependencies: List[Tuple[str, str]], output_path: str = "./dependency_results.txt") -> None:
    """将依赖关系结果保存到文件"""
    try:
        # 生成汇总文本
        summary_text = print_dependency_summary(dependencies)
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # 写入文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
        print(f"\n✅ 结果已保存到文件: {os.path.abspath(output_path)}")
    except Exception as e:
        print(f"\n❌ 保存结果文件失败: {e}")


def find_dependencies(operations: Dict[str, Dict[str, Any]]) -> List[Tuple[str, str]]:
    """查找接口依赖关系（基于字段级标识校验）"""
    print("\n" + "="*50)
    print("开始查找接口依赖关系")
    print("="*50)

    dependencies = []
    op_list = list(operations.items())
    total_ops = len(op_list)
    components = op_list[0][1].get("_components", {}) if op_list else {}
    for op_id, op_data in operations.items():
        op_data["_components"] = components

    for a_idx, (a_id, a_data) in enumerate(op_list):
        a_output = get_output_fields(a_data)
        if not a_output:
            continue  # 无出参的接口不作为上游

        if a_idx % 10 == 0:
            print(f"  进度: 处理第 {a_idx+1}/{total_ops} 个上游接口")

        for b_id, b_data in op_list:
            if a_id == b_id:
                continue  # 排除自身依赖

            b_input = get_input_fields(b_data)
            if not b_input:
                continue  # 无入参的接口不作为下游

            # 仅传递上下游字段信息
            if is_compatible(a_output, b_input):
                print(f"  ✅ 依赖成立: {a_id[:40]}... → {b_id[:40]}...")
                dependencies.append((a_id, b_id))

    print(f"\n✅ 依赖查找完成，共发现 {len(dependencies)} 组依赖关系")
    return dependencies


def print_dependency_summary(dependencies: List[Tuple[str, str]]) -> str:
    """生成汇总文本（终端只显示统计，文件保留完整依赖）"""
    summary_lines = []
    summary_lines.append("\n" + "="*60)
    summary_lines.append("                     接口依赖关系汇总")
    summary_lines.append("="*60)

    if not dependencies:
        summary_lines.append("❌ 未找到任何接口依赖关系")
        summary_lines.append("可能原因：")
        summary_lines.append("  1. 接口入参/出参字段无交集（可扩展 FIELD_MAPPING 映射表）")
        summary_lines.append("  2. 数组类型出参未包含有效字段（检查 schema 定义）")
        summary_lines.append("  3. 入参/出参业务语义不匹配（检查 RESOURCE_BUSINESS_TAG 映射）")
        summary_lines.append("  4. 部分接口无 2xx 响应或 content 定义")
    else:
        # 统计信息
        upstream_unique = len(set([op[0] for op in dependencies]))
        downstream_unique = len(set([op[1] for op in dependencies]))
        upstream_dep_count = {}
        for up, down in dependencies:
            upstream_dep_count[up] = upstream_dep_count.get(up, 0) + 1
        top_upstream = max(upstream_dep_count.items(), key=lambda x: x[1], default=(None, 0))

        summary_lines.append("\n📊 统计摘要：")
        summary_lines.append(f"  - 涉及上游接口总数: {upstream_unique} 个")
        summary_lines.append(f"  - 涉及下游接口总数: {downstream_unique} 个")
        summary_lines.append(f"  - 总依赖关系数量: {len(dependencies)} 组")
        if top_upstream[0]:
            summary_lines.append(f"  - 依赖最多的上游接口: {top_upstream[0][:50]}... （关联 {top_upstream[1]} 个下游接口）")

        # 完整依赖对
        file_only_lines = []
        file_only_lines.append("\n\n" + "="*40)
        file_only_lines.append("           完整依赖关系列表")
        file_only_lines.append("="*40)
        for i, (upstream_op, downstream_op) in enumerate(dependencies, 1):
            file_only_lines.append(f"\n{i:2d}. 上游接口 → 下游接口")
            file_only_lines.append(f"    上游: {upstream_op}")
            file_only_lines.append(f"    下游: {downstream_op}")

        # 汇总文本分为两部分：终端显示部分 + 文件专属部分
        terminal_text = "\n".join(summary_lines)
        full_text = terminal_text + "\n".join(file_only_lines)
        return full_text  

    return "\n".join(summary_lines)


def main(
    file_path: str = "./data/openapi.yaml",
    output_file: str = "./dependency_results.txt"
) -> None:
    print("="*60)
    print("           GitLab OpenAPI 接口依赖关系分析工具")
    print("="*60)

    try:
        print("\n1. 加载 OpenAPI 文件...")
        openapi_dict = load_openapi_dict(file_path)

        print("\n2. 提取接口操作信息...")
        operations = extract_operations_from_dict(openapi_dict)

        print("\n3. 解析引用关系（$ref）...")
        resolve_all_refs(operations, openapi_dict)

        print("\n4. 查找接口依赖关系...")
        dependencies = find_dependencies(operations)

        full_summary = print_dependency_summary(dependencies)
        terminal_summary = full_summary.split("\n\n" + "="*40)[0] if dependencies else full_summary
        print(terminal_summary)
        save_dependency_results(dependencies, output_file)

    except Exception as e:
        print(f"\n❌ 程序执行失败: {str(e)[:100]}")
        print("\n详细错误日志：")
        traceback.print_exc()
    finally:
        print("\n" + "="*60)
        print("程序执行结束")
        print("="*60)


if __name__ == "__main__":
    OPENAPI_FILE_PATH = './data/openapi.yaml' 
    RESULT_FILE_PATH = './outputs/dependency_results.txt' 
    main(file_path=OPENAPI_FILE_PATH, output_file=RESULT_FILE_PATH)