# backend/api/models.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from enum import Enum


class IntentType(str, Enum):
    """用户意图类型"""
    QUESTION = "question"
    OPERATION = "operation"


class StepStatus(str, Enum):
    """步骤状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class KnowledgeCategory(str, Enum):
    """知识库类别"""
    TABLE = "table"
    DOCUMENT = "document"
    SITEMAP = "sitemap"


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    site_id: str = Field(..., description="网站标识")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class ChatResponse(BaseModel):
    """聊天响应"""
    message: str = Field(..., description="AI回复消息")
    intent: IntentType = Field(..., description="识别的意图")
    code: Optional[str] = Field(None, description="testing-library代码")
    checklist: Optional[Dict[str, Any]] = Field(None, description="执行checklist")


class CodeExecutionResult(BaseModel):
    """代码执行结果"""
    status: str = Field(..., description="执行状态：success/failed")
    message: str = Field(..., description="执行结果描述")
    screenshot: Optional[str] = Field(None, description="截图base64")


class ExecutionFeedbackRequest(BaseModel):
    """执行反馈请求（从前端接收）"""
    status: str = Field(..., description="执行状态：success/failed")
    message: str = Field(..., description="执行结果描述")
    original_request: Optional[str] = Field(None, description="原始用户请求")
    site_id: Optional[str] = Field(None, description="网站标识")
    step_index: Optional[int] = Field(None, description="checklist步骤索引")


class ChecklistItem(BaseModel):
    """Checklist步骤项"""
    step: int = Field(..., description="步骤编号")
    description: str = Field(..., description="步骤描述")
    target_element: Optional[str] = Field(None, description="目标元素选择器")
    expected_result: str = Field(..., description="预期结果")
    status: StepStatus = Field(StepStatus.PENDING, description="步骤状态")


class Checklist(BaseModel):
    """完整Checklist"""
    plan: List[ChecklistItem] = Field(..., description="执行计划")
    progress: Dict[str, int] = Field(..., description="进度信息")
    errors: List[str] = Field([], description="错误列表")


class DocumentUpload(BaseModel):
    """文档上传请求"""
    filename: str = Field(..., description="文件名")
    content: bytes = Field(..., description="文件内容")
    site_id: str = Field(..., description="网站标识")


class AgentConfig(BaseModel):
    """Agent配置"""
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(..., description="Agent名称")
    id: str = Field(..., description="Agent唯一ID")
    description: str = Field(..., description="Agent描述")
    model_source: str = Field(..., description="使用的模型源名称")
    role: str = Field(..., description="角色定义")
    tools: List[str] = Field(..., description="可用工具列表")
    rules: List[str] = Field(..., description="执行规则")
    output_format: Dict[str, str] = Field(..., description="输出格式模板")


class DOMElement(BaseModel):
    """单个DOM元素"""
    type: str = Field(..., description="元素类型（button, input等）")
    selector: str = Field(..., description="CSS选择器")
    text: Optional[str] = Field(None, description="可见文本")
    position: Optional[Dict[str, int]] = Field(None, description="位置坐标")
    actions: List[str] = Field(default_factory=list, description="可执行操作")
    id: Optional[str] = Field(None, description="元素ID")


class DOMUploadRequest(BaseModel):
    """DOM元素上传请求"""
    site_id: Optional[str] = Field(None, description="[已废弃] 网站标识，请使用category+name")
    category: KnowledgeCategory = Field(KnowledgeCategory.SITEMAP, description="知识库类别")
    name: str = Field("default", description="库名称，每个类别下有默认库'default'")
    elements: List[DOMElement] = Field(..., description="DOM元素列表")


class OptimizationStrategy(BaseModel):
    """知识库优化策略"""
    id: str = Field(..., description="策略ID")
    name: str = Field(..., description="策略名称")
    score: float = Field(..., description="效果评分")
    core_idea: str = Field(..., description="核心思路")


class ElementUpdateRequest(BaseModel):
    """单条元素更新请求"""
    content: Optional[str] = Field(None, description="元素内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元素元数据")