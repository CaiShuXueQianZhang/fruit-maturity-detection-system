# =============================================================================
# AI 问答 API 路由模块
# =============================================================================
# 功能说明：
#   - 定义 AI 问答相关的 API 接口
#   - 支持单轮问答和多轮对话
#   - 支持流式响应
#
# API 接口列表：
#   POST /api/qa/ask          - 单轮问答（同步）
#   POST /api/qa/chat         - 多轮对话（同步）
#   POST /api/qa/stream       - 流式问答（实时推送）
#
# 使用示例：
#   # 单轮问答
#   POST /api/qa/ask
#   {
#       "question": "什么是水果成熟度检测？"
#   }
#
#   # 多轮对话
#   POST /api/qa/chat
#   {
#       "question": "它的准确率如何？",
#       "history": [
#           {"role": "user", "content": "什么是水果成熟度检测？"},
#           {"role": "assistant", "content": "水果成熟度检测是..."}
#       ]
#   }
# =============================================================================

from typing import List, Dict, Optional

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse

from app.services.qa_service import qa_service

# 创建 API 路由实例
router = APIRouter(prefix="/qa", tags=["qa"])


# =============================================================================
# 请求/响应模型
# =============================================================================
class AskRequest:
    """
    单轮问答请求模型
    """
    question: str


class ChatRequest:
    """
    多轮对话请求模型
    """
    question: str
    history: Optional[List[Dict[str, str]]] = None


class QAResponse:
    """
    问答响应模型
    """
    success: bool
    message: str
    answer: str
    history: Optional[List[Dict[str, str]]] = None


# =============================================================================
# 单轮问答接口
# =============================================================================
@router.post("/ask")
async def ask_question(
    question: str = Body(..., embed=True, description="用户问题")
):
    """
    单轮问答接口
    
    功能：
    - 接收用户问题
    - 调用 DeepSeek API 获取回答
    - 返回问答结果
    
    参数：
        question: 用户问题
    
    返回：
        {
            "success": true,
            "message": "问答成功",
            "answer": "AI 回答内容"
        }
    """
    try:
        # 调用问答服务
        answer = qa_service.ask(question)
        
        return {
            "success": True,
            "message": "问答成功",
            "answer": answer
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"问答失败: {str(e)}"
        )


# =============================================================================
# 多轮对话接口
# =============================================================================
@router.post("/chat")
async def chat(
    question: str = Body(..., description="用户问题"),
    history: Optional[List[Dict[str, str]]] = Body(None, description="历史对话记录")
):
    """
    多轮对话接口
    
    功能：
    - 支持多轮对话上下文
    - 调用 DeepSeek API 获取回答
    - 返回问答结果和更新后的对话历史
    
    参数：
        question: 用户问题
        history: 历史对话记录，格式为 [{"role": "user|assistant", "content": "..."}]
    
    返回：
        {
            "success": true,
            "message": "对话成功",
            "answer": "AI 回答内容",
            "history": [...]  // 更新后的对话历史
        }
    """
    try:
        # 调用问答服务
        answer = qa_service.ask(question, history)
        
        # 更新对话历史
        new_history = history.copy() if history else []
        new_history.append({"role": "user", "content": question})
        new_history.append({"role": "assistant", "content": answer})
        
        return {
            "success": True,
            "message": "对话成功",
            "answer": answer,
            "history": new_history
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"对话失败: {str(e)}"
        )


# =============================================================================
# 流式问答接口
# =============================================================================
@router.post("/stream")
async def stream_question(
    question: str = Body(..., embed=True, description="用户问题"),
    history: Optional[List[Dict[str, str]]] = Body(None, description="历史对话记录")
):
    """
    流式问答接口
    
    功能：
    - 实时推送 AI 回答内容
    - 支持多轮对话上下文
    - 使用 Server-Sent Events (SSE) 推送
    
    参数：
        question: 用户问题
        history: 历史对话记录（可选）
    
    返回：
        流式响应，逐块返回 AI 回答内容
    """
    try:
        # 生成流式响应
        def generate():
            for chunk in qa_service.ask_stream(question, history):
                yield chunk
        
        return StreamingResponse(
            generate(),
            media_type="text/plain; charset=utf-8"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"流式问答失败: {str(e)}"
        )


# =============================================================================
# 健康检查接口
# =============================================================================
@router.get("/health")
async def health_check():
    """
    问答服务健康检查接口
    
    返回：
        服务状态信息
    """
    api_key_configured = bool(qa_service.api_key and qa_service.api_key != "your_deepseek_api_key_here")
    
    return {
        "success": True,
        "message": "问答服务运行正常",
        "api_key_configured": api_key_configured,
        "model": qa_service.model
    }
