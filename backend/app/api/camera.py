# =============================================================================
# 摄像头实时检测 API 路由
# =============================================================================
import base64
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from app.services.detection_service import detection_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detection/camera", tags=["camera"])


class CameraFrameRequest(BaseModel):
    """摄像头帧请求模型"""
    image: str  # Base64 编码的图像数据
    confidence_threshold: Optional[float] = 0.5
    iou_threshold: Optional[float] = 0.45


class DetectionBoxResponse(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    class_name: str
    chinese_name: str


class CameraDetectionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@router.post("/detect", response_model=CameraDetectionResponse)
async def detect_frame(request: CameraFrameRequest):
    """
    接收前端摄像头帧并进行目标检测
    
    请求体:
        image: Base64 编码的图像 (data:image/jpeg;base64,xxx)
        confidence_threshold: 可选置信度阈值
        iou_threshold: 可选IOU阈值
    
    返回:
        检测框列表、帧统计信息
    """
    try:
        # 1. 提取 Base64 数据
        image_data = request.image
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        # 2. 解码为 OpenCV 图像 (BGR格式)
        image_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if image is None:
            return CameraDetectionResponse(
                success=False,
                message="图像解码失败"
            )
        
        # 3. 调用检测服务 (新增方法)
        result = detection_service.detect_image_array(
            image,
            confidence_threshold=request.confidence_threshold,
            iou_threshold=request.iou_threshold
        )
        
        return CameraDetectionResponse(
            success=True,
            message="检测成功",
            data=result
        )
        
    except Exception as e:
        logger.error(f"摄像头帧检测失败: {str(e)}")
        return CameraDetectionResponse(
            success=False,
            message=f"检测失败: {str(e)}"
        )
