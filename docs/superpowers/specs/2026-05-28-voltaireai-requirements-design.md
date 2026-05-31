# VoltaireAI.js 完整需求文档

**日期**：2026-05-28
**版本**：1.0
**状态**：已完善，待实现规划

---

## 项目概述
**项目名称**：voltaireAI.js
**项目目标**：让普通网站通过引入一行JS代码，即可支持AI操作和问答功能。

### 核心价值
- **简单集成**：一行代码即可启用AI能力
- **智能交互**：结合知识库和网站自动化
- **安全可控**：用户确认机制保障操作安全

---

## 前端部分

### 1. JS注入机制
**实现方式**：自动初始化完整系统
- 通过 `<script src="VOLTAIRE_BASE_URL/voltaire.js"></script>` 引入完整JS文件
- 自动初始化所有功能（悬浮按钮、对话框、通信）
- 通过全局变量 `VOLTAIRE_BASE_URL` 确认后端服务器地址

**一行代码示例**：
```html
<script src="https://your-server.com/voltaire.js"></script>
```

### 2. 悬浮按钮设计
**设计风格**：嵌套圆环（大小两个嵌入蓝色圆环）
- 外圆环包围内圆环，内环有填充色（半透明蓝色）
- 蓝色主题（#0066cc或类似）
- 支持拖拽功能（鼠标拖动自由移动）
- 默认位置：网页右下角悬浮
- 点击后弹出对话框（首次点击显示，再次点击隐藏）

**视觉实现**：
- 外圆环：直径60px，border宽度2px，颜色#0066cc，opacity 0.6
- 内圆环：直径40px，border宽度3px，颜色#0066cc，背景rgba(0,102,204,0.2)

### 3. 对话框设计
**布局风格**：聊天窗口风格（类似微信/WhatsApp）
- 消息左右分布：
  - 用户消息：右侧显示，蓝色背景，白色文字
  - AI回复：左侧显示，灰色背景，深色文字
- 对话记录存储在浏览器端（localStorage或sessionStorage）
- 离开页面后自动清空对话记录
- 支持Markdown解析（使用marked.js或类似库）
- 支持testing-library代码识别和执行

**对话框尺寸**：
- 默认：400px宽 × 500px高
- 可拖拽移动位置（标题栏拖动）
- 位置：悬浮按钮附近弹出（距离按钮20px）

**关闭方式**：
- 点击悬浮按钮切换显示/隐藏
- 点击对话框外部关闭
- ESC键关闭（可选）

**组件结构**：
```
对话框 = {
  header: 标题栏 + 关闭按钮,
  body: 对话记录区域（滚动）,
  footer: 输入框 + 发送按钮
}
```

### 4. 代码执行机制
**识别规则**：
- 当AI返回 `<js-start><js-end>` 包裹的代码时，识别为testing-library代码
- 正则表达式：`/<js-start>(.*?)<js-end>/`

**执行流程**：
1. AI返回包含代码的消息
2. 对话框显示代码内容预览（代码高亮）
3. 用户需点击"执行"按钮确认
4. 前端执行代码（使用testing-library API）
5. 执行后反馈结果给AI

**安全控制**：
- **用户确认机制**：所有代码执行前必须经过用户确认
- 显示代码内容预览，让用户看到即将执行的操作
- 提供"取消"按钮，用户可选择不执行

**反馈格式**：
```json
{
  "status": "success" | "failed",
  "message": "执行结果描述",
  "screenshot": "base64编码的截图（可选）"
}
```

### 5. 操作地图生成
**触发方式**：用户手动触发
- 对话框中提供"生成操作地图"按钮
- 用户点击按钮后开始扫描当前页面DOM

**扫描流程**：
1. 扫描当前页面DOM树
2. 提取可操作元素：button、form、input、select、a、div（有onclick）
3. 为每个元素生成摘要：
   - 元素类型、ID/Class、位置坐标、文本内容、可执行操作
4. 整理成JSON文档格式
5. 发送给后端存储

**元素摘要格式**：
```json
{
  "element_type": "button",
  "selector": "#submit-btn",
  "position": {"x": 100, "y": 200},
  "text": "提交",
  "actions": ["click"]
}
```

---

## 后端部分

### 1. 工作流设计

**Main流程**（默认调用）：
```
用户发出指令
  → LLM分析意图(问答/操作)
  → 调用知识库检索
  → 判断相关性
  → (失败则修正查询重试)
  → 创建checklist
  → 输出给前端
  → 前端执行代码
  → 反馈结果
  → 更新checklist
  → (失败则修正重试)
  → 完成
```

**意图识别机制**：
- 通过LLM自动分析用户问题
- 判断标准：
  - 包含操作关键词（点击、填写、提交、导航）→ 操作意图
  - 纯问题询问（是什么、如何、为什么）→ 问答意图
- 可配置意图识别Agent的提示词

**Checklist内容**：
```json
{
  "plan": [
    {
      "step": 1,
      "description": "找到登录按钮",
      "target_element": "#login-btn",
      "expected_result": "定位到登录按钮",
      "status": "pending"
    }
  ],
  "progress": {
    "total_steps": 3,
    "completed_steps": 0,
    "percentage": 0
  },
  "errors": []
}
```

**重试机制**：
- 知识库相关性判断失败：最多重试3次
- 代码执行失败：最多重试2次
- 每次重试时修正提示词或查询条件

**执行结果反馈处理**：
- 接收前端JSON反馈：{status, message, screenshot}
- 更新checklist状态
- 如果失败，分析错误原因，生成修正方案

### 2. 文档切片流程
**流程步骤**：
```
接收网页结构 → DOM元素节点切片 → LlamaIndex处理 → ChromaDB存储
```

**切片策略**：DOM元素节点切片
- 每个button、form、input、select等元素生成一个向量文档
- 文档内容包含：元素类型、选择器、位置、文本、操作类型

**切片示例**：
```json
{
  "id": "element-001",
  "content": "提交按钮，位于页面底部，selector: #submit-btn，可执行click操作",
  "metadata": {
    "element_type": "button",
    "selector": "#submit-btn",
    "page": "login"
  }
}
```

**LlamaIndex配置**：
- 切片大小：自适应（按元素）
- Embedding模型：可配置（OpenAI/本地模型）
- 索引方式：VectorStoreIndex

**ChromaDB管理**：
- 每个网站一个独立的collection
- 支持增删改查操作
- 向量维度：根据embedding模型确定

### 3. 知识库系统
**知识库结构**：
- 每个网站一个独立知识库
- 支持上传多种文档格式：PDF、DOCX、TXT、MD

**文档处理**：
- 上传后自动通过LlamaIndex切片
- 切片粒度：根据文档类型自适应
- 存入向量数据库

**检索机制**：
- 基于向量相似度检索
- 支持关键词过滤
- 返回最相关的top-k文档片段

### 4. Agent系统
**Agent类型**：
- 网站操作助手（通过testing-library生成操作代码）
- 知识问答助手（基于知识库回答问题）

**提示词结构**：
```yaml
role: "你是网站操作助手，帮助用户执行网站自动化操作"
tools:
  - testing-library
  - knowledge_query
rules:
  - "先理解用户意图，再生成代码"
  - "生成的代码必须包裹在<js-start><js-end>中"
  - "遇到错误时分析原因并修正"
output_format:
  code_template: "<js-start>\n// testing-library代码\n<js-end>"
  explanation: "用自然语言解释即将执行的操作"
```

**Agent配置存储**：
- 存储在JSON文件中：`backend/agents/agent_config.json`
- 支持动态加载和更新
- 版本管理：每次修改保存为新版本

---

## 后台管理系统

**整体布局**：顶部标签页风格
- 顶部导航条：显示"VoltaireAI后台"
- 下方标签页：知识库管理、Agent列表、设置
- 无需登录即可访问

### 1. 知识库管理页面
**设计风格**：卡片展示式
- 每个文档显示为独立卡片
- 卡片内容：文档图标、名称、大小、切片数量、上传时间

**功能模块**：
- **上传文档**：
  - 点击"上传文档"按钮
  - 选择文件（支持PDF、DOCX、TXT、MD）
  - 上传后自动切片，显示进度条
- **查看文档**：
  - 点击"查看"按钮
  - 弹出模态框显示文档内容
  - 仅查看，不可编辑
- **删除文档**：
  - 点击"删除"按钮
  - 确认后删除文档和向量数据

**卡片布局**：
```
卡片 = {
  icon: 文档图标（根据类型）,
  name: 文档名称,
  size: 文件大小（MB）,
  slices: 切片数量,
  upload_time: 上传时间,
  actions: [查看, 删除]
}
```

### 2. Agent列表页面
**设计风格**：扩展卡片式
- 每个Agent显示为扩展卡片
- 显示：图标、名称、ID、描述

**功能模块**：
- **创建Agent**：
  - 点击"创建Agent"按钮
  - 输入名称、描述、选择模型源
  - 编辑提示词
  - 保存配置
- **编辑提示词**：
  - 点击"编辑提示词"按钮
  - 弹出编辑器（支持Markdown）
  - 编辑角色、工具、规则、输出格式
  - 保存更新
- **删除Agent**：
  - 点击"删除"按钮
  - 确认后删除Agent配置

**卡片布局**：
```
Agent卡片 = {
  icon: Agent图标（可自定义）,
  name: Agent名称,
  id: Agent唯一ID,
  description: Agent描述,
  model_source: 使用的模型源,
  actions: [编辑提示词, 删除]
}
```

### 3. 设置页面
**功能模块**：

**模型配置**：
- 支持多个模型源配置
- 每个配置包含：
  - API格式：下拉选择（OpenAI、Anthropic、Custom）
  - Base URL：输入框
  - API Key：密码输入框
  - 模型名称：输入框（如gpt-4、claude-3-sonnet）
- 功能按钮：
  - 测试连接：验证配置是否正确
  - 删除配置：删除此模型源
  - 添加新模型源：新增配置项

**工作流设置**：
- 设置默认Main流程文件路径
- 输入框：显示当前路径（如workflows/main.json）
- 浏览文件按钮：选择流程文件

**保存设置**：
- 点击"保存所有设置"按钮
- 配置写入文件：`backend/config/settings.json`

---

## 技术栈

### 前端
- **JavaScript**：原生JS或轻量框架（Vanilla JS推荐）
- **Testing-library**：`@testing-library/dom`（用于网页自动化）
- **Markdown解析**：`marked.js`（Markdown转HTML）
- **样式**：CSS（可考虑轻量UI库，如TailwindCSS CDN）

### 后端
- **Python**：3.8+版本
- **LangChain**：工作流编排和Agent管理
- **LlamaIndex**：文档处理和向量索引
- **ChromaDB**：向量数据库（已安装）
- **HTTP框架**：FastAPI（推荐，高性能）或Flask
- **环境管理**：uv（Python包管理）

---

## 项目结构

```
voltaireAI/
├── frontend/
│   ├── voltaire.js              # 主注入文件（一行代码引入）
│   ├── components/
│   │   ├── floatingButton.js    # 悬浮按钮组件
│   │   ├── dialog.js            # 对话框组件
│   │   └── codeExecutor.js      # 代码执行器
│   │   └── markdownRenderer.js  # Markdown渲染器
│   ├── utils/
│   │   ├── domScanner.js        # DOM扫描器（生成操作地图）
│   │   ├── apiClient.js         # 后端API通信
│   │   └── localStorage.js      # 本地存储管理
│   └── styles/
│       ├── floatingButton.css   # 悬浮按钮样式
│       └── dialog.css           # 对话框样式
│
├── backend/
│   ├── main.py                  # FastAPI主程序
│   ├── config/
│   │   ├── settings.json        # 全局配置（模型、工作流）
│   │   └── agents.json          # Agent配置
│   ├── workflows/
│   │   ├── main.json            # Main流程定义
│   │   ├── document_slice.json  # 文档切片流程
│   │   ├── intent_analysis.json # 意图分析流程
│   │   └── execute_checklist.json # 执行checklist流程
│   ├── agents/
│   │   ├── agent_manager.py     # Agent管理器
│   │   ├── operation_agent.py   # 网站操作Agent
│   │   └── qa_agent.py          # 知识问答Agent
│   ├── knowledge/
│   │   ├── chromadb_manager.py  # ChromaDB管理
│   │   ├── llama_processor.py   # LlamaIndex处理
│   │   ├── document_upload.py   # 文档上传处理
│   │   └── vector_search.py     # 向量检索
│   ├── api/
│   │   ├── routes.py            # API路由定义
│   │   ├── models.py            # 数据模型（Pydantic）
│   │   ├── chat.py              # 聊天API
│   │   ├── knowledge.py         # 知识库API
│   │   ├── agent.py             # Agent API
│   │   └── workflow.py          # 工作流API
│   └── utils/
│       ├── intent_classifier.py # 意图分类器
│       ├── checklist_manager.py # Checklist管理
│       └── retry_handler.py     # 重试处理
│
├── admin/
│   ├── app.py                   # 后台管理应用（FastAPI）
│   ├── templates/
│   │   ├── base.html            # 基础模板
│   │   ├── knowledge.html       # 知识库管理页面
│   │   ├── agents.html          # Agent列表页面
│   │   ├── settings.html        # 设置页面
│   │   ├── agent_editor.html    # Agent编辑器
│   │   └── document_viewer.html # 文档查看器
│   ├── static/
│   │   ├── css/
│   │   │   ├── admin.css        # 后台样式
│   │   │   └── components.css   # 组件样式
│   │   ├── js/
│   │   │   ├── knowledge.js     # 知识库管理JS
│   │   │   ├── agents.js        # Agent管理JS
│   │   │   └── settings.js      # 设置管理JS
│   └── routes/
│       ├── knowledge.py         # 知识库路由
│       ├── agents.py            # Agent路由
│       └── settings.py          # 设置路由
│
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-28-voltaireai-requirements-design.md # 本文档
│
├── tests/
│   ├── frontend/
│   │   └── test_dialog.js       # 对话框测试
│   └── backend/
│       └── test_workflow.py     # 工作流测试
│
├── .venv/                       # Python虚拟环境
├── package.json                 # 前端依赖（@testing-library/dom）
├── requirements.txt             # Python依赖（可选）
└── README.md                    # 项目说明文档
```

---

## 需要进一步明确的问题

### 1. 工作流文件格式
**建议**：JSON格式（易读易修改）
- 每个流程文件包含：nodes（节点列表）、edges（连接关系）
- 节点类型：intent_analysis、knowledge_query、code_generation、execute

### 2. Agent配置存储
**建议**：JSON文件存储
- 文件路径：backend/config/agents.json
- 支持版本管理：每次修改备份旧版本

### 3. 知识库管理
**建议**：
- 知识库分类：按文档类型（产品文档、操作文档、FAQ）
- 文档去重：基于文件名和内容hash

### 4. 多网站支持
**建议**：
- 支持多网站：每个网站有独立的knowledge collection和agent配置
- 网站标识：通过VOLTAIRE_SITE_ID全局变量区分

### 5. 错误处理和日志
**建议**：
- 前端错误：详细堆栈信息 + 元素定位失败原因
- 后端日志：INFO级别，存储到logs/app.log

---

## 验证计划

### 前端验证
1. 注入JS后悬浮按钮正确显示
2. 点击按钮弹出对话框，布局正确
3. 输入问题后发送到后端，接收回复
4. AI返回代码后显示预览，用户确认执行
5. 执行结果正确反馈给AI
6. 对话记录正确存储和清空

### 后端验证
1. Main流程正确识别意图
2. 知识库检索返回相关内容
3. Checklist正确创建和更新
4. 代码执行失败后正确重试
5. 文档切片正确存储到ChromaDB

### 后台管理验证
1. 知识库管理页面正确上传、查看、删除文档
2. Agent列表页面正确创建、编辑、删除Agent
3. 设置页面正确配置模型和工作流

---

## 总结

本需求文档已完善所有主要功能设计：
- ✅ 前端UI设计：悬浮按钮、对话框、代码执行机制
- ✅ 后端工作流：Main流程、意图识别、Checklist管理
- ✅ 知识库系统：文档切片、向量存储、检索机制
- ✅ Agent系统：提示词结构、配置管理
- ✅ 后台管理：三个核心页面的详细设计
- ✅ 技术栈和项目结构：完整的文件组织

接下来可以进入实现规划阶段，使用superpowers:writing-plans技能创建详细的实现计划。