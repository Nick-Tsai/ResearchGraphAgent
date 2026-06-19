# Research Graph Agent

> 一个面向学习者的 AI 研究助手——输入一个主题，自动拆解、搜索、提炼、构建知识图谱，最终生成图文并茂的学习文章。

## 功能

- **IDPS 问题分解** — 自动将主题拆解为多个维度 + 子问题 + 证伪测试，判断受众级别（小学/初中/高中/大学）
- **多源搜索** — Firecrawl 自部署 IP 池轮询（25 节点），Tavily 降级，Mock 兜底
- **语义分类器** — 纯 Python TF-IDF + 余弦相似度，零 LLM 调用，evidence → dimension 确定性映射
- **维度并行图构建** — IDPS dimension 为分组单位并行调 LLM，全局审查生成跨维度边
- **文章生成** — 8 步学习路径（概述→重要性→核心概念→深入→应用→误解→小测验→进一步探索）
- **Token 追踪** — per-run 预算 200k，每个 LLM 阶段自动统计 + 超限拦截
- **LaTeX 数学渲染** — `$...$` / `$$...$$` / `\[...\]` 全支持
- **学习伴侣 UI** — 树形知识图谱 + 研究资料折叠面板 + 文章优先视图 + 中文化界面

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11+, FastAPI, SQLModel, SQLite (WAL), pytest |
| 前端 | Next.js 16 (App Router), TypeScript, Tailwind CSS v4 |
| LLM | DeepSeek V4 Flash (1M context), mock provider 可选 |
| 搜索 | Firecrawl 自部署 IP 池 + Tavily 降级 |
| 数学 | KaTeX + remark-math + rehype-katex |
| 分类 | 自研 TF-IDF 分类器（零外部依赖） |

## 快速开始

### 后端

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 填入 API key
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 前端

```bash
cd frontend
npm install
npx next dev --port 3000
```

打开 `http://localhost:3000`，输入研究主题即可开始。

### 测试

```bash
cd backend
PYTHONPATH=. ./venv/bin/pytest app/tests/ -v
```

## 配置

关键环境变量（`backend/.env`）：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MODEL_PROVIDER` | `mock` | LLM 提供商：`mock` / `deepseek` |
| `SEARCH_PROVIDER` | `mock` | 搜索：`mock` / `tavily` / `firecrawl` |
| `DEEPSEEK_API_KEY` | — | DeepSeek API key |
| `TAVILY_API_KEY` | — | Tavily API key（Firecrawl 降级备用） |

Firecrawl 自部署 IP 池配置在 `backend/firecrawl_pool.json`（已 gitignore）：

```json
{
  "instances": [
    {"url": "http://ip:3002", "api_key": "", "weight": 1}
  ]
}
```

## 项目结构

```
ResearchGraphAgent/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── models.py        # SQLModel 数据模型
│   │   ├── schemas.py       # Pydantic 校验
│   │   ├── db.py            # 数据库引擎
│   │   ├── config.py        # 环境变量
│   │   ├── pipeline/        # 流水线（IDPS/搜索/摘要/图构建/审查）
│   │   ├── providers/       # LLM + 搜索 provider
│   │   └── tests/           # pytest 测试
│   ├── requirements.txt
│   ├── .env.example
│   └── firecrawl_pool.json
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # 首页（topic 输入 + 项目列表）
│   │   └── projects/[id]/   # 项目详情页（学习路径 + 图谱 + 文章）
│   └── lib/                 # API 客户端 + 类型 + 工具函数
├── research-graph-agent.md  # 产品规格 + 实现路线图
└── AGENTS.md               # 贡献者指南
```

## 流水线架构

```
用户输入 topic
  → IDPS 分解（自动判断受众级别）
  → 搜索（Firecrawl IP 池 → Tavily → Mock）
  → 摘要 + 证据提取（DeepSeek，受众自适应）
  → 语义分类（TF-IDF，零 LLM）
  → 图构建（维度并行，保留原始子问题）
  → 审查（全局跨维度分析）
  → 文章生成（8 步学习路径）
```

## 里程碑

- [x] M1: 本地骨架
- [x] M2: IDPS 计划
- [x] M3: 搜索 + 源提取
- [x] M4: 摘要 + 证据
- [x] M5: 图构建
- [x] M6: 节点操作（展开/挑战）
- [x] M7: 高级审查
- [x] M8: 文章生成 + 学习路径
- [x] M9: Token 追踪 + 预算控制
- [x] M10: 语义分类器 + 维度 DSL

## Production Roadmap

详见 [research-graph-agent.md §16](research-graph-agent.md).

## 贡献

请阅读 [AGENTS.md](AGENTS.md) 了解代码规范、测试指南和 PR 流程。

## License

MIT
