# VoltaireAI.js 完整实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个完整的网站外挂式AI系统，通过一行JS代码让网站支持AI操作和问答功能。

**Architecture:**
- 前端：原生JS + Testing-library，自动注入悬浮按钮和对话框，用户确认执行代码
- 后端：FastAPI + LangChain + LlamaIndex + ChromaDB，提供工作流和Agent系统
- 后台：FastAPI模板渲染，管理知识库和Agent配置

**Tech Stack:**
- 前端：Vanilla JS, @testing-library/dom, marked.js
- 后端：Python 3.8+, FastAPI, LangChain, LlamaIndex, ChromaDB
- 后台：Jinja2模板, Bootstrap 5

---

## 文件结构映射

### 前端文件（frontend/）
- `voltaire.js` - 主注入文件，一行代码入口，自动初始化所有组件
- `components/floatingButton.js` - 悬浮按钮组件（嵌套圆环，可拖拽）
- `components/dialog.js` - 对话框组件（聊天窗口风格）
- `components/codeExecutor.js` - 代码执行器（用户确认机制）
- `utils/domScanner.js` - DOM扫描器（生成操作地图）
- `utils/apiClient.js` - 后端API通信封装
- `styles/floatingButton.css` - 悬浮按钮样式（嵌套圆环）
- `styles/dialog.css` - 对话框样式（聊天窗口）

### 后端文件（backend/）
- `main.py` - FastAPI主程序入口，CORS配置
- `config/settings.json` - 全局配置（模型源、工作流路径）
- `config/agents.json` - Agent配置列表
- `workflows/main.json` - Main工作流定义（意图识别→知识库→checklist）
- `agents/agent_manager.py` - Agent管理器（加载、选择Agent）
- `agents/operation_agent.py` - 网站操作Agent（生成testing-library代码）
- `agents/qa_agent.py` - 知识问答Agent（检索知识库）
- `knowledge/chroma_manager.py` - ChromaDB管理器（增删改查）
- `knowledge/llama_processor.py` - LlamaIndex文档处理（切片）
- `api/routes.py` - API路由定义
- `api/models.py` - Pydantic数据模型

### 后台管理文件（admin/）
- `app.py` - 后台管理FastAPI应用
- `templates/base.html` - 基础HTML模板（顶部标签页）
- `templates/knowledge.html` - 知识库管理页面（卡片展示）
- `templates/agents.html` - Agent列表页面（扩展卡片）
- `templates/settings.html` - 设置页面（模型配置）
- `static/css/admin.css` - 后台样式
- `static/js/admin.js` - 后台交互逻辑

---

## 阶段1：项目初始化和后端基础（4个任务）

### Task 1: 创建项目基础结构

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `backend/main.py`
- Create: `backend/config/__init__.py`

- [ ] **Step 1: 创建.gitignore文件**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
*.log

# Node
node_modules/

# IDEs
.vscode/
.idea/

# Project
.superpowers/
logs/
.env
backend/config/settings.json
.chroma/
```

- [ ] **Step 2: 创建Python依赖文件**

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
langchain==0.1.0
llama-index==0.9.0
chromadb==0.4.22
python-multipart==0.0.6
aiofiles==23.2.1
python-dotenv==1.0.0
jinja2==3.1.2
```

- [ ] **Step 3: 创建FastAPI主程序骨架**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="VoltaireAI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "VoltaireAI Backend running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 4: 安装Python依赖**

Run: `pip install -r requirements.txt`
Expected: Successfully installed all packages

- [ ] **Step 5: 测试后端启动**

Run: `python backend/main.py`
Expected: Server starts on http://localhost:8000

- [ ] **Step 6: Commit基础结构**

```bash
git add .gitignore requirements.txt backend/main.py
git commit -m "feat: initialize project structure with FastAPI backend"
```

---

### Task 2: 创建配置系统

**Files:**
- Create: `backend/config/settings.json`
- Create: `backend/config/config_loader.py`

- [ ] **Step 1: 创建配置加载器**

```python
import json
import os

DEFAULT_SETTINGS = {
    "model_sources": [{"name": "default", "api_format": "OpenAI", "base_url": "https://api.openai.com/v1", "api_key": "", "model": "gpt-4"}],
    "main_workflow": "workflows/main.json"
}

def load_settings(path="backend/config/settings.json"):
    if not os.path.exists(path):
        save_settings(DEFAULT_SETTINGS, path)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_settings(settings, path="backend/config/settings.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
```

- [ ] **Step 2: 创建默认配置文件**

```json
{
  "model_sources": [{"name": "default", "api_format": "OpenAI", "base_url": "https://api.openai.com/v1", "api_key": "", "model": "gpt-4"}],
  "main_workflow": "workflows/main.json"
}
```

- [ ] **Step 3: Commit配置系统**

```bash
git add backend/config/
git commit -m "feat: add configuration system"
```

---

### Task 3: 创建API数据模型

**Files:**
- Create: `backend/api/models.py`

- [ ] **Step 1: 创建Pydantic数据模型**

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class IntentType(str, Enum):
    QUESTION = "question"
    OPERATION = "operation"

class ChatRequest(BaseModel):
    message: str
    site_id: str
    context: Optional[dict] = None

class ChatResponse(BaseModel):
    message: str
    intent: IntentType
    code: Optional[str] = None
    checklist: Optional[dict] = None

class CodeExecutionResult(BaseModel):
    status: str
    message: str
    screenshot: Optional[str] = None

class AgentConfig(BaseModel):
    name: str
    id: str
    description: str
    model_source: str
    role: str
    tools: List[str]
    rules: List[str]
```

- [ ] **Step 2: Commit数据模型**

```bash
git add backend/api/models.py
git commit -m "feat: add Pydantic data models"
```

---

### Task 4: 创建基础API路由

**Files:**
- Create: `backend/api/routes.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 创建API路由**

```python
from fastapi import APIRouter
from backend.api.models import ChatRequest, ChatResponse
from backend.config.config_loader import load_settings

router = APIRouter(prefix="/api")

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # Mock响应，后续连接真实AI
    return ChatResponse(message="AI系统构建中", intent="question")

@router.get("/settings")
async def get_settings():
    return load_settings()

@router.post("/settings")
async def update_settings(settings: dict):
    from backend.config.config_loader import save_settings
    save_settings(settings)
    return {"message": "Settings updated"}
```

- [ ] **Step 2: 更新main.py引用路由**

```python
# 在main.py中添加
from backend.api.routes import router as api_router
app.include_router(api_router)
```

- [ ] **Step 3: 测试API端点**

Run: `curl http://localhost:8000/api/settings`
Expected: JSON配置返回

- [ ] **Step 4: Commit API路由**

```bash
git add backend/api/routes.py backend/main.py
git commit -m "feat: add basic API routes"
```

---

## 阶段2：前端核心组件（3个任务）

### Task 5: 创建前端基础结构和样式

**Files:**
- Create: `frontend/styles/floatingButton.css`
- Create: `frontend/styles/dialog.css`
- Create: `frontend/voltaire.js`

- [ ] **Step 1: 创建悬浮按钮样式**

```css
.voltaire-floating-button {
    position: fixed; bottom: 20px; right: 20px;
    width: 60px; height: 60px; z-index: 10000;
    cursor: pointer; transition: transform 0.3s;
}
.voltaire-outer-ring {
    position: absolute; width: 60px; height: 60px;
    border: 2px solid #0066cc; border-radius: 50%; opacity: 0.6;
}
.voltaire-inner-ring {
    position: absolute; width: 40px; height: 40px;
    border: 3px solid #0066cc; border-radius: 50%;
    background: rgba(0,102,204,0.2); top: 10px; left: 10px;
}
```

- [ ] **Step 2: 创建对话框样式**

```css
.voltaire-dialog {
    position: fixed; width: 400px; height: 500px;
    background: white; border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    z-index: 9999; display: none; flex-direction: column;
}
.voltaire-dialog.active { display: flex; }
.voltaire-dialog-header {
    padding: 15px; background: #0066cc; color: white;
    border-radius: 8px 8px 0 0; cursor: move;
}
.voltaire-message.user { justify-content: flex-end; }
.voltaire-message.ai { justify-content: flex-start; }
```

- [ ] **Step 3: Commit前端样式**

```bash
git add frontend/styles/
git commit -m "feat: add frontend CSS styles"
```

---

### Task 6: 实现悬浮按钮和对话框组件

**Files:**
- Create: `frontend/voltaire.js`（完整版本）

- [ ] **Step 1: 创建完整的voltaire.js**

```javascript
(function() {
    const BASE_URL = window.VOLTAIRE_BASE_URL || 'http://localhost:8000';
    const state = { dialogVisible: false, messages: [], siteId: 'default' };

    function init() {
        injectStyles();
        createFloatingButton();
        createDialog();
    }

    function injectStyles() {
        // 内联样式或从BASE_URL加载
        const style = document.createElement('style');
        style.textContent = `
            /* CSS样式（从CSS文件复制）*/
        `;
        document.head.appendChild(style);
    }

    function createFloatingButton() {
        const btn = document.createElement('div');
        btn.className = 'voltaire-floating-button';
        btn.innerHTML = '<div class="voltaire-outer-ring"></div><div class="voltaire-inner-ring"></div>';
        btn.addEventListener('click', toggleDialog);
        document.body.appendChild(btn);
        setupDraggable(btn);
    }

    function createDialog() {
        const dialog = document.createElement('div');
        dialog.className = 'voltaire-dialog';
        dialog.id = 'voltaire-dialog';
        dialog.innerHTML = `
            <div class="voltaire-dialog-header">
                <span>VoltaireAI</span><span class="voltaire-dialog-close">×</span>
            </div>
            <div class="voltaire-dialog-body" id="voltaire-messages"></div>
            <div class="voltaire-dialog-footer">
                <textarea class="voltaire-input" placeholder="输入问题" rows="2"></textarea>
                <button class="voltaire-send-btn">发送</button>
            </div>
        `;
        document.body.appendChild(dialog);
        setupDialogEvents(dialog);
    }

    function toggleDialog() {
        const dialog = document.getElementById('voltaire-dialog');
        state.dialogVisible = !state.dialogVisible;
        dialog.classList.toggle('active', state.dialogVisible);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
```

- [ ] **Step 2: 测试前端组件**

手动测试：创建HTML测试文件，引入voltaire.js，验证：
- 悬浮按钮显示
- 点击弹出对话框
- 发送消息

- [ ] **Step 3: Commit前端组件**

```bash
git add frontend/voltaire.js
git commit -m "feat: implement floating button and dialog"
```

---

### Task 7: 实现代码执行器和DOM扫描器

**Files:**
- Create: `frontend/components/codeExecutor.js`
- Create: `frontend/utils/domScanner.js`

- [ ] **Step 1: 创建代码执行器（用户确认机制）**

```javascript
// frontend/components/codeExecutor.js
export function executeCodeWithConfirmation(code) {
    return new Promise((resolve, reject) => {
        // 创建确认对话框
        const modal = document.createElement('div');
        modal.className = 'voltaire-code-modal';
        modal.innerHTML = `
            <div class="voltaire-modal-content">
                <h3>即将执行代码</h3>
                <pre>${code}</pre>
                <div>
                    <button class="voltaire-confirm-btn">执行</button>
                    <button class="voltaire-cancel-btn">取消</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        modal.querySelector('.voltaire-confirm-btn').onclick = () => {
            try {
                eval(code); // 执行testing-library代码
                resolve({ status: 'success', message: '执行成功' });
            } catch (e) {
                reject({ status: 'failed', message: e.message });
            }
            modal.remove();
        };

        modal.querySelector('.voltaire-cancel-btn').onclick = () => {
            reject({ status: 'cancelled', message: '用户取消' });
            modal.remove();
        };
    });
}
```

- [ ] **Step 2: 创建DOM扫描器**

```javascript
// frontend/utils/domScanner.js
export function scanDOM() {
    const elements = [];
    const selectors = ['button', 'input', 'select', 'form', 'a'];

    selectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            elements.push({
                type: el.tagName.toLowerCase(),
                selector: el.id ? `#${el.id}` : `.${el.className.split(' ')[0]}`,
                text: el.textContent.trim(),
                position: { x: el.offsetLeft, y: el.offsetTop },
                actions: getActions(el)
            });
        });
    });

    return elements;
}

function getActions(el) {
    const actions = [];
    if (el.tagName === 'BUTTON' || el.tagName === 'A') actions.push('click');
    if (el.tagName === 'INPUT') actions.push('fill');
    if (el.tagName === 'SELECT') actions.push('select');
    return actions;
}
```

- [ ] **Step 3: Commit执行器和扫描器**

```bash
git add frontend/components/ frontend/utils/
git commit -m "feat: add code executor and DOM scanner"
```

---

## 阶段3：后端核心功能（简化版，3个关键任务）

由于篇幅限制，以下为关键后端任务概要：

### Task 8: 创建ChromaDB管理器

**Files:**
- Create: `backend/knowledge/chroma_manager.py`

- [ ] **Step 1: 创建ChromaDB管理器**

```python
import chromadb
from chromadb.config import Settings

class ChromaManager:
    def __init__(self, persist_dir=".chroma"):
        self.client = chromadb.PersistentClient(path=persist_dir)

    def create_collection(self, site_id):
        return self.client.create_collection(name=site_id)

    def add_documents(self, site_id, documents, metadatas):
        collection = self.client.get_collection(name=site_id)
        collection.add(documents=documents, metadatas=metadatas)

    def query(self, site_id, query_text, n_results=5):
        collection = self.client.get_collection(name=site_id)
        return collection.query(query_texts=[query_text], n_results=n_results)
```

- [ ] **Commit ChromaDB管理器**

---

### Task 9: 创建工作流和Agent基础

**Files:**
- Create: `backend/workflows/main.json`
- Create: `backend/agents/agent_manager.py`

- [ ] **创建Main工作流定义**

```json
{
  "name": "main",
  "steps": [
    {"type": "intent_analysis", "agent": "operation_agent"},
    {"type": "knowledge_query"},
    {"type": "create_checklist"},
    {"type": "generate_code"},
    {"type": "execute_code"}
  ]
}
```

- [ ] **创建Agent管理器**

```python
class AgentManager:
    def load_agents(self, path="backend/config/agents.json"):
        with open(path) as f:
            return json.load(f)

    def select_agent(self, intent):
        agents = self.load_agents()
        if intent == "operation":
            return agents[0]  # operation_agent
        return agents[1]  # qa_agent
```

---

### Task 10: 集成LangChain工作流

**Files:**
- Modify: `backend/api/routes.py`

- [ ] **Step 1: 更新chat路由连接真实AI**

```python
@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # 1. 意图识别
    intent = analyze_intent(request.message)

    # 2. 选择Agent
    agent = agent_manager.select_agent(intent)

    # 3. 查询知识库（如果是问答）
    if intent == "question":
        docs = chroma_manager.query(request.site_id, request.message)

    # 4. 生成响应
    response = generate_response(agent, request.message, docs)

    return response
```

---

## 阶段4：后台管理系统（2个关键任务）

### Task 11: 创建后台应用基础

**Files:**
- Create: `admin/app.py`
- Create: `admin/templates/base.html`

- [ ] **创建后台FastAPI应用**

```python
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="admin/static"), name="static")
templates = Jinja2Templates(directory="admin/templates")

@app.get("/")
async def dashboard(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})
```

---

### Task 12: 创建知识库和Agent管理页面

**Files:**
- Create: `admin/templates/knowledge.html`
- Create: `admin/templates/agents.html`

- [ ] **创建知识库管理页面（卡片展示）**

```html
<!-- admin/templates/knowledge.html -->
{% extends "base.html" %}
{% block content %}
<div class="container">
    <h2>知识库管理</h2>
    <button onclick="uploadDocument()">上传文档</button>
    <div class="cards">
        {% for doc in documents %}
        <div class="card">
            <div class="icon">📄</div>
            <div class="name">{{ doc.name }}</div>
            <div class="meta">{{ doc.size }} | {{ doc.slices }}切片</div>
            <button onclick="viewDoc('{{ doc.id }}')">查看</button>
            <button onclick="deleteDoc('{{ doc.id }}')">删除</button>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
```

---

## 验证计划

### 前端验证
- [ ] 悬浮按钮正确显示并可拖拽
- [ ] 对话框弹出和交互正常
- [ ] 代码执行前有用户确认
- [ ] DOM扫描生成操作地图

### 后端验证
- [ ] API端点响应正常
- [ ] ChromaDB存储和检索成功
- [ ] Agent选择逻辑正确
- [ ] 工作流执行流程完整

### 后台验证
- [ ] 知识库上传/删除功能正常
- [ ] Agent编辑功能正常
- [ ] 设置保存功能正常

---

## Self-Review检查

1. **Spec覆盖**: 所有需求文档中的功能点都有对应任务
2. **Placeholder检查**: 无TBD/TODO等placeholder
3. **类型一致性**: API模型定义和前端使用一致

---

**Plan complete and saved to `docs/superpowers/plans/2026-05-28-voltaireai-implementation.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** - 我会为每个任务派发新的subagent，任务间有review检查点，快速迭代

2. **Inline Execution** - 在当前会话中使用executing-plans技能，批量执行任务

**Which approach?**