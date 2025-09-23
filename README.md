# GitLab API 语义依赖分析

用 Qwen3-Embedding-0.6B 对 GitLab REST API 做语义嵌入，阈值 0.74 构建依赖图。

## 结果（对于Qwen3）
- 模块纯度 79.2%，边数 380，孤立节点 10 个
- 推荐阈值：0.74（纯度-数量拐点）

## 文件
outputs/
├── embeddings_qwen3.npy        # Qwen3 向量
├── dependencies_qwen3.json     # 最终依赖图（阈值0.74）
├── dependency_graph_qwen3.png  # 可视化图
├── threshold_curve_qwen3.txt   # 阈值-纯度曲线
├── compare_dependencies_result.txt   # MiniLM vs Qwen3 对比
└── tag_purity_result.txt       # 模块纯度报告

models/                         # 需手动下载大模型
src/                            # 全部脚本
├── 02_embed_qwen3.py           # 生成 embedding
├── 03_build_dependencies_v2.py # 构建依赖（参数化阈值）
├── 04_visualize_v2.py          # 可视化
├── compare_dependencies.py     # 量化对比
├── tag_purity.py               # 模块纯度
└── threshold_curve.py          # 阈值曲线

## 复现
1. 下载模型到 models/ 目录
2. python src/02_embed_qwen3.py
3. python src/03_build_dependencies_v2.py --emb outputs/embeddings_qwen3.npy --thresh 0.74
4. python src/04_visualize_v2.py --dep outputs/dependencies_qwen3.json
