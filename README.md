# GitLab API 语义依赖分析

用 Qwen3-Embedding-0.6B 对 GitLab REST API 做语义嵌入，阈值 0.74 构建依赖图。

## 结果（对于Qwen3）
- 模块纯度 79.2%，边数 380，孤立节点 10 个
- 推荐阈值：0.74（纯度-数量拐点）

## 文件
Gitlab-Api-Embedding/  
├── README.md                           # 本文件  
├── requirements.txt                    # 依赖包列表  
├── data/  
│   └── openapi.yaml                    # 原始 OpenAPI 文件  
├── models/  
│   ├── all-MiniLM-L6-v2/               # MiniLM 模型（需下载）  
│   └── Qwen3-Embedding-0.6B/           # Qwen3 模型（需下载）  
├── outputs/  
│   ├── compare_dependencies_result.txt # MiniLM vs Qwen3 量化对比  
│   ├── dependencies.json               # MiniLM 依赖图（对比用）  
│   ├── dependencies_qwen3.json         # Qwen3 最终依赖图（阈值0.74）  
│   ├── dependency_graph.png            # MiniLM 可视化（对比用）  
│   ├── dependency_graph_qwen3.png      # Qwen3 可视化图  
│   ├── embeddings.npy                  # MiniLM 向量（对比用）  
│   ├── embeddings_qwen3.npy            # Qwen3 向量  
│   ├── operations.json                 # 提取的 operation 列表  
│   ├── tag_purity_result.txt           # 模块纯度报告  
│   └── threshold_curve_qwen3.txt       # 阈值-纯度曲线  
└── src/  
├── build_dependencies.py           # 构建依赖（参数化阈值）  
├── compare_dependencies.py         # 量化对比  
├── embed_operations.py             # MiniLM embedding（对比用）  
├── embed_qwen3.py                  # 生成 Qwen3 embedding  
├── parse_openapi.py                # 提取 operation  
├── tag_purity.py                   # 模块纯度计算  
├── threshold_curve.py              # 阈值曲线  
└── visualize.py                    # 可视化（对比用）  

## 复现
1. 下载模型到 models/ 目录
2. python src/02_embed_qwen3.py
3. python src/03_build_dependencies_v2.py --emb outputs/embeddings_qwen3.npy --thresh 0.74
4. python src/04_visualize_v2.py --dep outputs/dependencies_qwen3.json
