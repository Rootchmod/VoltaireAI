# backend/main.py
import os
import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn

# 导入API路由（使用相对导入）
from api.routes import router as api_router

app = FastAPI(
    title="VoltaireAI Backend",
    description="AI-powered website automation and Q&A system",
    version="1.0.0"
)

# CORS配置(允许前端跨域访问)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 规范化 URL 路径：将连续的 // 替换为单个 /
@app.middleware("http")
async def normalize_path_middleware(request: Request, call_next):
    # 规范化路径：移除连续的斜杠
    path = request.url.path
    if "//" in path:
        normalized_path = re.sub(r"/+", "/", path)
        # 创建新的请求对象，替换路径
        request.scope["path"] = normalized_path
        request.scope["raw_path"] = normalized_path.encode()
    response = await call_next(request)
    return response

# 处理 Private Network Access (PNA) 预检请求
@app.middleware("http")
async def add_pna_headers(request, call_next):
    response = await call_next(request)
    # 允许从公网访问本地私有网络
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

# 注册API路由
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": "VoltaireAI Backend is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/VoltaireAI/admin", response_class=HTMLResponse)
@app.get("/VoltaireAI/admin/", response_class=HTMLResponse)
async def admin_page():
    """返回管理页面"""
    admin_html_path = os.path.join(os.path.dirname(__file__), "admin.html")
    if os.path.exists(admin_html_path):
        return FileResponse(admin_html_path, media_type="text/html")
    return HTMLResponse(content="<h1>Admin page not found</h1>", status_code=404)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)