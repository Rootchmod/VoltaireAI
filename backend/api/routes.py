# backend/api/routes.py
import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse

from api.models import (
    ChatRequest, ChatResponse, DOMUploadRequest, ExecutionFeedbackRequest,
    KnowledgeCategory, OptimizationStrategy, ElementUpdateRequest,
)
from workflows.workflow_engine import get_workflow_engine
from knowledge.chroma_manager import get_chroma_manager, _is_default_collection, _make_collection_name, _parse_collection_name
from knowledge.llama_processor import get_llama_processor
from knowledge.strategies import get_all_strategies, DEFAULT_STRATEGY_ID, get_strategy_by_id
from agents.agent_manager import get_agent_manager
from config.config_loader import load_settings, save_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/VoltaireAI", tags=["api"])

# Get workflow engine and knowledge managers
workflow_engine = get_workflow_engine()
chroma_manager = get_chroma_manager()
llama_processor = get_llama_processor()
agent_manager = get_agent_manager()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    处理聊天请求 - 使用真实AI工作流

    Args:
        request: ChatRequest包含message, site_id, optional context

    Returns:
        ChatResponse with AI response, intent, optional code
    """
    try:
        # Execute workflow to get real AI response
        response = workflow_engine.execute_chat_workflow(request)
        return response
    except Exception as e:
        logger.error(f"Chat workflow failed: {e}")
        # Fallback to error message
        return ChatResponse(
            message=f"抱歉，处理您的请求时发生错误：{str(e)}",
            intent="question",
            code=None,
            checklist=None
        )

@router.get("/chat/stream")
async def chat_stream(
    message: str = Query(..., description="用户消息"),
    site_id: str = Query("default", description="网站标识")
):
    """
    SSE 实时进度流端点

    使用 Server-Sent Events 推送工作流执行进度。
    前端用 EventSource 消费，连接失败时 fallback 到 POST /api/chat。
    """
    async def event_generator():
        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        # Run synchronous generator in executor, pushing events into the queue
        def run_workflow():
            try:
                for event in workflow_engine.execute_chat_workflow_stream(message, site_id):
                    loop.call_soon_threadsafe(queue.put_nowait, event)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, {
                    "type": "error",
                    "message": str(e)
                })
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        task = loop.run_in_executor(None, run_workflow)

        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        await task

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/settings")
async def get_settings():
    """
    获取当前配置

    Returns:
        Current settings including model sources and workflow
    """
    settings = load_settings()
    return settings

@router.post("/settings")
async def update_settings(settings: dict):
    """
    更新配置

    Args:
        settings: New settings dictionary

    Returns:
        Success message
    """
    # TODO: 添加配置验证（Phase 2）
    save_settings(settings)
    return {"message": "Settings updated successfully"}


@router.post("/upload-dom")
async def upload_dom_elements(request: DOMUploadRequest):
    """
    上传DOM元素到知识库

    Args:
        request: DOMUploadRequest包含category, name和elements列表

    Returns:
        Success message with element count
    """
    try:
        # Backward compat: support old site_id parameter
        category = request.category.value if hasattr(request.category, 'value') else request.category
        col_name = request.name

        # Convert Pydantic models to dictionaries
        elements_data = []
        for i, element in enumerate(request.elements):
            elements_data.append({
                "id": element.id or f"elem_{i}",
                "type": element.type,
                "selector": element.selector,
                "text": element.text or "",
                "position": element.position or {},
                "actions": element.actions
            })

        # Process and store elements
        llama_processor.process_and_store(
            elements_data,
            category=category,
            name=col_name,
            chroma_manager=chroma_manager
        )

        logger.info(f"Uploaded {len(elements_data)} elements to {category}_{col_name}")

        return {
            "message": "DOM elements uploaded successfully",
            "category": category,
            "name": col_name,
            "element_count": len(elements_data)
        }
    except Exception as e:
        logger.error(f"DOM upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/execution-feedback")
async def execution_feedback(request: ExecutionFeedbackRequest):
    """
    接收前端代码执行反馈

    Args:
        request: ExecutionFeedbackRequest包含执行状态、消息、原始请求

    Returns:
        下一步操作指引 (继续/重试/终止)
    """
    try:
        result = workflow_engine.handle_execution_feedback(request)
        logger.info(f"Feedback processed: {result.get('next_action')}")

        # If retry requested, provide new code to frontend
        if result.get("next_action") == "retry" and result.get("retry_code"):
            return {
                "status": "retry",
                "message": result.get("message", ""),
                "retry_code": result.get("retry_code")
            }

        return {"status": result.get("status", "acknowledged"), "message": result.get("message", "")}
    except Exception as e:
        logger.error(f"Feedback processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Feedback processing failed: {str(e)}")


# ═══════════════════════════════════════════════════════════
# Admin API
# ═══════════════════════════════════════════════════════════

@router.get("/admin/collections")
async def admin_list_collections():
    """列出所有知识库集合（按类别分组）"""
    try:
        collections = chroma_manager.list_collections()
        # Group by category
        grouped = {"table": [], "document": [], "sitemap": []}
        for col in collections:
            cat = col.get("category", "unknown")
            if cat in grouped:
                grouped[cat].append(col)
            else:
                grouped[cat] = [col]
        return {"collections": collections, "grouped": grouped, "total": len(collections)}
    except Exception as e:
        logger.error(f"List collections failed: {e}")
        return {"collections": [], "grouped": {}, "total": 0}


@router.get("/admin/collections/{category}/{name}")
async def admin_get_collection(category: str, name: str):
    """获取指定知识库的所有元素详情"""
    try:
        if category not in ("table", "document", "sitemap"):
            raise HTTPException(status_code=400, detail=f"无效的类别: {category}")
        elements = chroma_manager.get_elements(category, name)
        return {
            "category": category,
            "name": name,
            "collection_name": _make_collection_name(category, name),
            "is_default": _is_default_collection(_make_collection_name(category, name)),
            "element_count": len(elements),
            "elements": elements
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get collection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get collection failed: {str(e)}")


@router.delete("/admin/collections/{category}/{name}")
async def admin_delete_collection(category: str, name: str):
    """删除指定知识库（默认库不可删除）"""
    try:
        if category not in ("table", "document", "sitemap"):
            raise HTTPException(status_code=400, detail=f"无效的类别: {category}")
        chroma_manager.delete_collection(category, name)
        return {"message": f"知识库 {category}_{name} 已删除", "category": category, "name": name}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete collection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.delete("/admin/collections/{category}/{name}/elements/{element_id}")
async def admin_delete_element(category: str, name: str, element_id: str):
    """删除知识库中的单条元素"""
    try:
        if category not in ("table", "document", "sitemap"):
            raise HTTPException(status_code=400, detail=f"无效的类别: {category}")
        collection_name = _make_collection_name(category, name)
        deleted = chroma_manager.delete_element(collection_name, element_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"元素 {element_id} 未找到")
        return {"message": f"元素 {element_id} 已删除", "element_id": element_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete element failed: {e}")
        raise HTTPException(status_code=500, detail=f"Delete element failed: {str(e)}")


@router.put("/admin/collections/{category}/{name}/elements/{element_id}")
async def admin_update_element(category: str, name: str, element_id: str, update: ElementUpdateRequest):
    """编辑知识库中的单条元素"""
    try:
        if category not in ("table", "document", "sitemap"):
            raise HTTPException(status_code=400, detail=f"无效的类别: {category}")
        collection_name = _make_collection_name(category, name)
        updated = chroma_manager.update_element(
            collection_name, element_id,
            content=update.content,
            metadata=update.metadata
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"元素 {element_id} 未找到")
        return {"message": f"元素 {element_id} 已更新", "element_id": element_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update element failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update element failed: {str(e)}")


@router.post("/admin/collections")
async def admin_create_collection(data: dict):
    """创建新的知识库集合"""
    try:
        category = data.get("category", "")
        name = data.get("name", "")
        description = data.get("description", "")
        if category not in ("table", "document", "sitemap"):
            raise HTTPException(status_code=400, detail=f"无效的类别: {category}")
        if not name or not name.strip():
            raise HTTPException(status_code=400, detail="库名称不能为空")
        chroma_manager.create_collection(category, name, description=description)
        return {"message": f"知识库 {category}_{name} 创建成功", "category": category, "name": name, "description": description}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create collection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Create collection failed: {str(e)}")


@router.put("/admin/collections/{category}/{name}")
async def admin_update_collection(category: str, name: str, data: dict):
    """更新知识库集合（备注描述）"""
    try:
        if category not in ("table", "document", "sitemap"):
            raise HTTPException(status_code=400, detail=f"无效的类别: {category}")
        description = data.get("description", "")
        updated = chroma_manager.update_collection_description(category, name, description)
        if not updated:
            raise HTTPException(status_code=404, detail=f"知识库 {category}_{name} 未找到")
        return {"message": f"知识库 {category}_{name} 已更新", "category": category, "name": name, "description": description}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update collection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Update collection failed: {str(e)}")


@router.post("/admin/documents/upload")
async def admin_upload_document(
    file: UploadFile = File(..., description="要上传的文件"),
    site_id: str = Form(None, description="[已废弃] 网站标识"),
    category: str = Form("document", description="知识库类别 (table/document/sitemap)"),
    name: str = Form("default", description="库名称"),
    strategy_id: str = Form(None, description="优化策略ID")
):
    """上传文档到知识库，支持优化策略处理"""
    try:
        if category not in ("table", "document", "sitemap"):
            raise HTTPException(status_code=400, detail=f"无效的类别: {category}")

        content = await file.read()
        text_content = content.decode('utf-8', errors='replace')

        if strategy_id is None:
            strategy_id = DEFAULT_STRATEGY_ID

        # Use document processing with optimization
        llama_processor.process_document_and_store(
            content=text_content,
            filename=file.filename,
            chroma_manager=chroma_manager,
            category=category,
            name=name,
            strategy_id=strategy_id,
        )

        strategy = get_strategy_by_id(strategy_id)
        logger.info(f"Uploaded document {file.filename} to {category}_{name} with strategy {strategy_id}")

        return {
            "message": "文档上传成功",
            "filename": file.filename,
            "category": category,
            "name": name,
            "size": len(text_content),
            "strategy": strategy["name"] if strategy else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/admin/agents")
async def admin_list_agents():
    """列出所有Agent"""
    try:
        agents = agent_manager.list_agents()
        return {"agents": agents, "total": len(agents)}
    except Exception as e:
        logger.error(f"List agents failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/agents/{agent_id}")
async def admin_update_agent(agent_id: str, config: dict):
    """更新或创建Agent"""
    try:
        updated = agent_manager.update_agent(agent_id, config)
        if updated:
            return {"message": f"Agent {agent_id} 已更新", "agent": updated}
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update agent failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/agents/{agent_id}")
async def admin_delete_agent(agent_id: str):
    """删除Agent"""
    try:
        deleted = agent_manager.delete_agent(agent_id)
        if deleted:
            return {"message": f"Agent {agent_id} 已删除"}
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete agent failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/settings/test-connection")
async def admin_test_connection(config: dict):
    """测试LLM API连接（使用真实chat调用验证）"""
    try:
        base_url = config.get("base_url", "")
        api_key = config.get("api_key", "")
        model = config.get("model", "")

        if not base_url or not api_key:
            return {"status": "error", "message": "请填写完整的API配置"}

        # Test with an actual chat completion call to validate the key
        import requests as http_req
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model or "deepseek-chat",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 5
        }
        url = base_url.rstrip("/") + "/chat/completions"

        resp = http_req.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            return {"status": "success", "message": f"连接成功 (模型: {model})"}
        else:
            err_body = resp.json().get("error", {}).get("message", "") if resp.text else ""
            return {"status": "error", "message": f"连接失败: HTTP {resp.status_code} {err_body}"}
    except Exception as e:
        logger.error(f"Test connection failed: {e}")
        return {"status": "error", "message": f"连接失败: {str(e)}"}


# ═══════════════════════════════════════════════════════════
# Optimization Strategies
# ═══════════════════════════════════════════════════════════

@router.get("/admin/optimization-strategies")
async def admin_get_strategies():
    """获取所有可用的知识库优化策略"""
    try:
        strategies = get_all_strategies()
        return {
            "strategies": strategies,
            "total": len(strategies),
            "default": DEFAULT_STRATEGY_ID,
        }
    except Exception as e:
        logger.error(f"Get strategies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Sitemap Generator
# ═══════════════════════════════════════════════════════════

@router.post("/admin/sitemap/generate")
async def admin_generate_sitemap(data: dict):
    """触发Playwright站点地图生成（一次性工具）"""
    url = data.get("url", "")
    name = data.get("name", "default")

    if not url:
        raise HTTPException(status_code=400, detail="请提供目标URL")

    try:
        from tools.sitemap_generator import generate_sitemap
        result = generate_sitemap(
            url=url,
            name=name,
            upload_to_api="http://localhost:8001",
        )
        if result.get("status") == "error":
            return {"status": "error", "message": result.get("message", "生成失败")}
        return {
            "status": "success",
            "message": f"站点地图已生成并存入 sitemap_{name}",
            "element_count": result.get("element_count", 0),
            "tag_counts": result.get("tag_counts", {}),
        }
    except ImportError:
        raise HTTPException(status_code=501, detail="Playwright 未安装，请运行: pip install playwright && playwright install chromium")
    except Exception as e:
        logger.error(f"Sitemap generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"站点地图生成失败: {str(e)}")


@router.get("/admin/sitemap/generate-stream")
async def admin_generate_sitemap_stream(
    url: str,
    name: str = "default",
    login_url: str = None,
    username: str = None,
    password: str = None,
    login_submit_selector: str = None,
    manual_login: bool = False,
    cookies_file: str = None,
    explore: bool = True,
    max_depth: int = 5,
    max_total_clicks: int = 80,
):
    """SSE 实时进度流 - 站点地图生成"""
    import asyncio
    from tools.sitemap_generator import generate_sitemap

    async def event_generator():
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()

        def progress_callback(step, message, data=None):
            # Thread-safe: schedule into the event loop
            loop.call_soon_threadsafe(
                lambda s=step, m=message, d=data: asyncio.ensure_future(
                    queue.put((s, m, d))
                )
            )

        # Set default cookies file path
        actual_cookies = cookies_file or (".voltaire_knowledge/cookies.json" if login_url else None)

        # Run Playwright in a thread (it's synchronous)
        gen_task = asyncio.ensure_future(
            loop.run_in_executor(
                None,
                lambda: generate_sitemap(
                    url=url,
                    name=name,
                    headless=not manual_login,
                    upload_to_api="http://localhost:8001",
                    progress_callback=progress_callback,
                    login_url=login_url,
                    username=username,
                    password=password,
                    login_submit_selector=login_submit_selector,
                    manual_login=manual_login,
                    cookies_file=actual_cookies,
                    explore=explore,
                    max_depth=max_depth,
                    max_total_clicks=max_total_clicks,
                )
            )
        )

        # Stream progress as it arrives
        while not gen_task.done() or not queue.empty():
            try:
                step, msg, dt = await asyncio.wait_for(queue.get(), timeout=0.2)
                payload = json.dumps({"step": step, "message": msg, "data": dt}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            except asyncio.TimeoutError:
                continue

        # Get result and send completion
        try:
            result = await gen_task
            final = json.dumps({
                "step": "complete",
                "message": "站点地图生成完成" if result.get("status") == "success" else "生成失败",
                "data": {
                    "status": result.get("status"),
                    "element_count": result.get("element_count", 0),
                    "tag_counts": result.get("tag_counts", {}),
                    "name": name,
                    "error": result.get("message") if result.get("status") == "error" else None,
                }
            }, ensure_ascii=False)
            yield f"data: {final}\n\n"
        except Exception as e:
            error_payload = json.dumps({"step": "error", "message": str(e), "data": None}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ═══════════════════════════════════════════════════════════
# Backward Compatibility - old site_id-based endpoints
# ═══════════════════════════════════════════════════════════

@router.get("/admin/collections/{site_id}")
async def admin_get_collection_legacy(site_id: str):
    """
    [向后兼容] 旧格式：单段路径。
    重定向到新的category/name格式。
    """
    # Treat old site_id as name under sitemap or detect from existing collections
    collections = chroma_manager.list_collections()
    match = None
    for col in collections:
        if col.get("display_name") == site_id or col.get("name") == site_id:
            match = col
            break
        # Also check legacy site_xxx naming
        if col.get("name") == f"site_{site_id}":
            match = col
            break

    if match:
        return await admin_get_collection(match["category"], match["display_name"])

    # Fallback: try as sitemap category
    return await admin_get_collection("sitemap", site_id)


@router.delete("/admin/collections/{site_id}")
async def admin_delete_collection_legacy(site_id: str):
    """
    [向后兼容] 旧格式：单段路径删除。
    映射到新的category/name格式。
    """
    collections = chroma_manager.list_collections()
    match = None
    for col in collections:
        if col.get("display_name") == site_id or col.get("name") == site_id:
            match = col
            break
        if col.get("name") == f"site_{site_id}":
            match = col
            break

    if match:
        return await admin_delete_collection(match["category"], match["display_name"])

    # Fallback: try as sitemap category
    return await admin_delete_collection("sitemap", site_id)