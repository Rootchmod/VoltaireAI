# VoltaireAI — 网站外挂式 AI 助手

一行 `<script>` 标签，让任何网站拥有 AI 驱动的智能助手——既能回答用户关于网站的问题，也能代替用户执行页面操作（点击、填写、导航等）。

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 快速开始

```bash
pip install -r requirements.txt
cd backend && python main.py
```

在目标网站中添加：
```html
<script src="http://localhost:8001/voltaire.js"></script>
```

## 完整文档

详细文档请访问 GitHub Pages：**[项目文档站点](https://your-username.github.io/your-repo/)**

或直接查看 `docs/index.html`。

## 架构

```
用户消息 → 意图分类(LLM) → Agent选择 → 知识库查询(ChromaDB) → LLM代码生成 → 前端执行
                                                                         ↓
                                                              Testing Library 沙箱
                                                                         ↓
                                                              执行反馈 → 失败重试
```

## 核心特性

- **意图驱动**：LLM 自动区分"操作"与"问题"请求
- **知识库增强**：每次对话自动查询页面元素、操作步骤、文档资料
- **代码生成+执行**：AI 生成 JS 代码，前端 Testing Library 沙箱安全执行
- **流式推送**：SSE 实时展示处理进度
- **失败重试**：执行失败自动反馈错误上下文给 LLM 重新生成
- **配置驱动**：所有 Agent 提示词通过 JSON 文件管理，无需改代码
- **站点地图工具**：Playwright 驱动的一次性网站扫描+智能探索

## 目录结构

```
├── backend/          # FastAPI 后端
│   ├── api/          # 数据模型 + API 路由
│   ├── config/       # 系统设置 + Agent 配置
│   ├── agents/       # Agent 加载与管理
│   ├── llm/          # LangChain LLM 客户端
│   ├── workflows/    # 意图分类 + 工作流引擎
│   ├── knowledge/    # ChromaDB 知识库 + 优化策略
│   └── tools/        # Playwright 站点地图生成器
├── frontend/
│   ├── voltaire.js   # 注入脚本 (vanilla JS)
│   └── admin.html    # 管理后台 SPA
└── docs/             # 文档
```

## 许可证

MIT
