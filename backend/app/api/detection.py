# =============================================================================
# 检测 API 路由模块
# =============================================================================
# 功能说明：
#   - 定义检测相关的 API 接口
#   - 处理图片上传、检测请求、结果返回
#   - 提供历史记录和目标类别查询接口
#   - 检测结果持久化存储到 PostgreSQL 数据库
#
# API 接口列表：
#   POST /api/detection/single    - 单图检测
#   GET  /api/detection/history   - 获取检测历史记录（从数据库）
#   GET  /api/detection/{id}      - 获取单个检测记录
#   DELETE /api/detection/{id}    - 删除检测记录
#   GET  /api/detection/targets/list - 获取可检测目标列表
#
# 使用示例：
#   # 前端调用
#   const formData = new FormData();
#   formData.append('file', imageFile);
#   formData.append('model_name', 'mab-yolo11m');
#   const response = await fetch('/api/detection/single', {
#       method: 'POST',
#       body: formData
#   });
# =============================================================================

# 导入 os 模块，用于文件路径操作
import os
import tempfile

# 导入 FastAPI 相关组件
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Path, Response, Request
from typing import Any, Dict, List
import json
import cv2

# 导入检测服务
from app.services.detection_service import detection_service

# 导入 MinIO 服务
from app.services.minio_service import minio_service

# 导入文件工具函数
from app.utils.file_utils import save_upload_file, ensure_directories

# 导入应用配置
from app.config import settings

# 导入数据模型
from app.models.schemas import (
    SingleDetectionResponse,   # 单图检测响应模型
    BatchDetectionResponse,
    HistoryResponse,          # 历史记录响应模型
    TargetListResponse,       # 目标列表响应模型
    TargetItem,               # 目标项数据模型
    HistoryItem               # 历史记录项数据模型
)

# 导入数据库模型
from app.models.database import DetectionRecord, get_db

# 创建 API 路由实例
# prefix: 所有路由的前缀，如 /api/detection
# tags: 用于 OpenAPI 文档分组
router = APIRouter(prefix="/detection", tags=["detection"])

# 在模块加载时确保必要的目录存在
ensure_directories()

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def _decode_storage_value(value: Any) -> Any:
    if not value:
        return None
    if isinstance(value, (list, dict)):
        return value
    value_text = str(value).strip()
    try:
        return json.loads(value_text)
    except Exception:
        parts = [item.strip() for item in value_text.split(",") if item.strip()]
        return parts if len(parts) > 1 else value_text


def _storage_values(value: Any) -> List[str]:
    parsed = _decode_storage_value(value)
    if isinstance(parsed, list):
        return [str(item) for item in parsed if item]
    if isinstance(parsed, dict):
        return [str(item) for item in parsed.values() if item]
    if parsed:
        return [str(parsed)]
    return []


def _first_storage_value(value: Any) -> str:
    values = _storage_values(value)
    return values[0] if values else ""


def _object_name_from_key(key: str) -> str:
    return os.path.basename(str(key)) if key else ""


def _is_video_key(key: str) -> bool:
    return os.path.splitext(_object_name_from_key(key))[1].lower() in VIDEO_EXTENSIONS


def _bucket_for_key(default_bucket: str, key: str) -> str:
    if str(key).startswith("uploads/"):
        return settings.minio.original_bucket
    if str(key).startswith("results/"):
        return settings.minio.results_bucket
    return default_bucket


def _file_url(default_bucket: str, key: str) -> str:
    object_name = _object_name_from_key(key)
    if not object_name:
        return ""
    bucket = _bucket_for_key(default_bucket, key)
    return f"http://localhost:8000/api/detection/files/{bucket}/{object_name}"


def _result_media(value: Any) -> Dict[str, str]:
    parsed = _decode_storage_value(value)
    if isinstance(parsed, dict):
        cover_key = parsed.get("cover") or parsed.get("cover_image") or parsed.get("thumbnail") or ""
        video_key = parsed.get("video") or parsed.get("video_key") or parsed.get("result_video") or ""
        fallback_key = cover_key or video_key or _first_storage_value(parsed)
        return {"cover": str(cover_key) if cover_key else "", "video": str(video_key) if video_key else "", "fallback": str(fallback_key) if fallback_key else ""}

    first_key = _first_storage_value(parsed)
    if _is_video_key(first_key):
        return {"cover": "", "video": first_key, "fallback": first_key}
    return {"cover": first_key, "video": "", "fallback": first_key}


def _persist_result_media(record_id: str, media: Dict[str, str]) -> None:
    db_gen = get_db()
    db = next(db_gen)
    try:
        record = db.query(DetectionRecord).filter(DetectionRecord.id == record_id).first()
        if record:
            record.result_image_key = json.dumps(media, ensure_ascii=False)
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db_gen.close()


def _ensure_video_cover(record: DetectionRecord, original_key: str, media: Dict[str, str]) -> Dict[str, str]:
    if (record.type or "") != "video" or media.get("cover"):
        return media

    source_key = media.get("video") or original_key
    if not source_key:
        return media

    bucket = _bucket_for_key(settings.minio.results_bucket, source_key)
    object_name = _object_name_from_key(source_key)
    if not object_name:
        return media

    response = None
    temp_path = ""
    try:
        response = minio_service.client.get_object(bucket, object_name)
        video_bytes = response.read()
        suffix = os.path.splitext(object_name)[1] or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(video_bytes)
            temp_path = temp_file.name

        capture = cv2.VideoCapture(temp_path)
        success, frame = capture.read()
        capture.release()
        if not success or frame is None:
            return media

        encoded, image_bytes = cv2.imencode(".jpg", frame)
        if not encoded:
            return media

        cover_object_name = minio_service.upload_result_image(image_bytes.tobytes(), "jpg")
        cover_key = f"results/{cover_object_name}"
        updated_media = {"video": media.get("video") or source_key, "cover": cover_key}
        _persist_result_media(str(record.id), updated_media)
        return {"cover": cover_key, "video": updated_media["video"], "fallback": cover_key}
    except Exception:
        return media
    finally:
        if response:
            try:
                response.close()
                response.release_conn()
            except Exception:
                pass
        if temp_path:
            try:
                os.remove(temp_path)
            except Exception:
                pass


# =============================================================================
# 单图检测接口
# =============================================================================

@router.post("/single", response_model=SingleDetectionResponse)
async def detect_single_image(
    file: UploadFile = File(...),      # 上传的图片文件（必填）
    model_name: str = Form("mab-yolo11m"), # 使用的模型名称（可选）
    user_id: str = Form(None)          # 用户 ID（可选）
):
    """
    单图目标检测接口

    功能：
    - 接收用户上传的图片
    - 保存图片到服务器
    - 调用检测服务进行目标检测
    - 保存检测记录到数据库
    - 返回检测结果

    参数：
        file: 上传的图片文件，支持 jpg、png 等格式
        model_name: 使用的模型名称（可选，默认 mab-yolo11m）
        user_id: 用户 ID（可选）

    返回：
        SingleDetectionResponse: 包含检测结果的响应

    响应示例：
        {
            "success": true,
            "message": "检测成功",
            "data": {
                "detection_id": "uuid-string",
                "image_url": "http://localhost:8000/static/uploads/xxx.jpg",
                "result_image_url": "http://localhost:8000/static/results/xxx.jpg",
                "boxes": [...],
                "total_objects": 5,
                "detection_time": 0.523,
                "model_name": "mab-yolo11m",
                "created_at": "2024-12-01T14:30:00"
            }
        }
    """
    try:
        # 确保临时上传目录存在
        os.makedirs(settings.upload_dir, exist_ok=True)
        
        # 保存上传的文件到服务器
        # save_upload_file 是异步函数，使用 await 调用
        filename = await save_upload_file(file, settings.upload_dir)

        # 构建图片的完整路径
        image_path = os.path.join(settings.upload_dir, filename)

        # 调用检测服务进行单图检测（支持用户 ID）
        result = detection_service.detect_single_image(image_path, user_id, model_name, minio_service)

        # 检测完成后，删除临时上传的文件（节省空间）
        try:
            os.remove(image_path)
        except:
            pass  # 删除失败不影响流程

        # 返回成功的响应
        return SingleDetectionResponse(
            success=True,                    # 请求成功
            message="检测成功",             # 提示信息
            data=result                      # 检测结果数据
        )

    except FileNotFoundError as e:
        # 模型文件未找到
        raise HTTPException(
            status_code=500,
            detail="模型文件未找到"
        )
    except Exception as e:
        # 如果检测过程中发生错误，抛出 500 错误
        raise HTTPException(
            status_code=500,                 # HTTP 状态码：服务器内部错误
            detail=f"检测失败: {str(e)}"    # 详细错误信息
        )


# =============================================================================
# 批量图片检测接口
# =============================================================================
@router.post("/batch", response_model=BatchDetectionResponse)
async def detect_batch_images(
    request: Request,
    files: List[UploadFile] = File(None),
    model_name: str = Form("mab-yolo11m"),
    user_id: str = Form(None)
):
    """
    批量图片检测接口（更健壮）：
    - 优先使用框架绑定的 `files`
    - 如果绑定为空，则从原始表单中解析（支持 files, files[] 或 file）
    """
    try:
        os.makedirs(settings.upload_dir, exist_ok=True)

        # 如果 FastAPI 未正确绑定 files，则从表单解析
        parsed_files = []
        if files:
            parsed_files = files
        else:
            form = await request.form()
            # 打印 form 的 keys 与类型，便于调试
            try:
                print("[批量检测] form keys:", list(form.keys()))
                for k in form.keys():
                    v = form.getlist(k) if hasattr(form, 'getlist') else [form.get(k)]
                    types = [type(x).__name__ for x in v]
                    print(f"[批量检测] key={k}, types={types}")
            except Exception:
                pass

            # 尝试从 form 中提取所有 UploadFile 实例
            for v in form.values():
                if isinstance(v, UploadFile):
                    parsed_files.append(v)
            # 兼容性：有些客户端会将字段名作为 files[]
            # model_name / user_id 也可能在 form 中
            if not model_name:
                model_name = form.get('model_name') or model_name
            if not user_id:
                user_id = form.get('user_id') or user_id

        # 调试输出接收到的文件数量
        try:
            print(f"[批量检测] 接收到文件数量: {len(parsed_files)}")
        except Exception:
            pass

        # 如果没有接收到文件，返回错误，提示前端检查请求
        if len(parsed_files) == 0:
            raise HTTPException(status_code=400, detail="未收到上传文件（请检查前端请求的表单字段名与 Content-Type）")

        # 保存所有上传文件到本地临时目录
        saved_paths = []
        for file in parsed_files:
            filename = await save_upload_file(file, settings.upload_dir)
            saved_paths.append(os.path.join(settings.upload_dir, filename))

        # 调用检测服务进行批量检测（同步执行）
        batch_results = detection_service.detect_batch_images(saved_paths, user_id=user_id, model_name=model_name)

        # 清理临时文件
        for p in saved_paths:
            try:
                os.remove(p)
            except:
                pass

        return BatchDetectionResponse(success=True, message="批量检测完成", data=batch_results)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量检测失败: {str(e)}")


# =============================================================================
# 视频文件检测接口
# =============================================================================
@router.post("/video", response_model=SingleDetectionResponse)
async def detect_video_file(
    file: UploadFile = File(...),
    model_name: str = Form("mab-yolo11m"),
    user_id: str = Form(None)
):
    """
    视频文件检测接口
    接收单个视频文件，逐帧检测并返回处理后的视频访问 URL
    """
    video_path = None
    try:
        os.makedirs(settings.upload_dir, exist_ok=True)

        filename = await save_upload_file(file, settings.upload_dir)
        video_path = os.path.join(settings.upload_dir, filename)

        result = detection_service.detect_video(video_path, user_id=user_id, model_name=model_name)

        return SingleDetectionResponse(success=True, message="视频检测完成", data=result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视频检测失败: {str(e)}")
    finally:
        if video_path:
            try:
                os.remove(video_path)
            except Exception:
                pass


# =============================================================================
# 摄像头/帧检测接口（用于实时预览）
# =============================================================================
@router.post("/frame")
async def detect_frame(
    file: UploadFile = File(...),
    model_name: str = Form("mab-yolo11m")
):
    """
    接收单帧图像字节，返回检测框、帧尺寸和检测耗时。
    前端使用实时视频流显示画面，只按检测频率更新检测框。
    """
    try:
        data = await file.read()
        frame_result = detection_service.detect_frame(data, model_name=model_name)

        return {
            "success": True,
            "message": "帧检测成功",
            "data": {
                "boxes": frame_result.get("boxes", []),
                "width": frame_result.get("width", 0),
                "height": frame_result.get("height", 0),
                "detection_time": frame_result.get("detection_time", 0)
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"帧检测失败: {str(e)}")


# =============================================================================
# 检测历史记录接口
# =============================================================================

@router.get("/history", response_model=HistoryResponse)
async def get_detection_history(
    page: int = 1,        # 页码（从 1 开始）
    page_size: int = 10,   # 每页记录数
    user_id: str = None    # 用户 ID（可选）
):
    """
    获取检测历史记录接口

    功能：
    - 从 PostgreSQL 数据库查询检测历史记录
    - 支持分页查询
    - 支持按用户 ID 筛选

    参数：
        page: 页码，默认 1
        page_size: 每页记录数，默认 10
        user_id: 用户 ID（可选）

    返回：
        HistoryResponse: 包含历史记录列表的响应

    响应示例：
        {
            "success": true,
            "message": "获取成功",
            "data": [
                {
                    "id": "uuid-string",
                    "image_url": "http://localhost:8000/static/uploads/xxx.jpg",
                    "result_image_url": "http://localhost:8000/static/results/xxx.jpg",
                    "total_objects": 3,
                    "created_at": "2024-12-01T14:30:00",
                    "model_name": "mab-yolo11m"
                },
                ...
            ],
            "total": 15
        }
    """
    try:
        # 调用检测服务获取历史记录
        records = detection_service.get_detection_history(user_id=user_id, limit=page_size * page)

        # 计算分页
        start = (page - 1) * page_size
        end = start + page_size

        # 转换为 HistoryItem 列表
        history_items = []
        for record in records[start:end]:
            original_list = _storage_values(record.original_image_key)
            original_key = original_list[0] if original_list else ""
            media = _result_media(record.result_image_key)
            if (record.type or "") == "video":
                media = _ensure_video_cover(record, original_key, media)

            count = max(len(original_list), 1)

            original_filename = _object_name_from_key(original_key)
            image_url = _file_url(settings.minio.original_bucket, original_key)
            if (record.type or "") == "video":
                result_url = _file_url(settings.minio.results_bucket, media.get("cover", ""))
                video_url = _file_url(settings.minio.results_bucket, media.get("video", ""))
                cover_url = result_url
                filename = original_filename or _object_name_from_key(media.get("video", "")) or "video.mp4"
            else:
                result_url = _file_url(settings.minio.results_bucket, media.get("cover") or media.get("fallback", ""))
                video_url = ""
                cover_url = ""
                filename = original_filename or "detection.jpg"

            history_items.append(HistoryItem(
                id=str(record.id),
                image_url=image_url,
                result_image_url=result_url,
                video_url=video_url,
                cover_image_url=cover_url,
                total_objects=record.total_objects or 0,
                created_at=record.created_at,
                model_name=record.model_name or "mab-yolo11m",
                filename=filename,
                status=record.status or "completed",
                type=record.type or "single",
                time=record.created_at.strftime("%Y-%m-%d %H:%M") if record.created_at else "",
                count=count,
                detected_targets=[]  # 暂时留空
            ))

        # 返回历史记录响应
        return HistoryResponse(
            success=True,                          # 请求成功
            message="获取成功",                     # 提示信息
            data=history_items,                    # 当前页的数据
            total=len(records)                     # 总记录数
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取历史记录失败: {str(e)}"
        )


# =============================================================================
# 获取单个检测记录接口
# =============================================================================

@router.get("/detail/{detection_id}", response_model=SingleDetectionResponse)
@router.get("/{detection_id}", response_model=SingleDetectionResponse)
async def get_detection_by_id(
    detection_id: str = Path(..., description="检测记录 ID")
):
    """
    获取单个检测记录接口

    功能：
    - 根据检测 ID 从数据库查询详细检测记录

    参数：
        detection_id: 检测记录 ID

    返回：
        SingleDetectionResponse: 包含检测结果的响应
    """
    try:
        # 调用检测服务获取检测记录
        record = detection_service.get_detection_by_id(detection_id)

        if not record:
            raise HTTPException(
                status_code=404,
                detail="检测记录不存在"
            )

        original_key = _first_storage_value(record.original_image_key)
        media = _result_media(record.result_image_key)
        if (record.type or "") == "video":
            media = _ensure_video_cover(record, original_key, media)

        image_url = _file_url(settings.minio.original_bucket, original_key)
        if (record.type or "") == "video":
            cover_url = _file_url(settings.minio.results_bucket, media.get("cover", ""))
            video_url = _file_url(settings.minio.results_bucket, media.get("video", ""))
            result_url = cover_url or video_url
        else:
            cover_url = ""
            video_url = ""
            result_url = _file_url(settings.minio.results_bucket, media.get("cover") or media.get("fallback", ""))

        # 构建响应数据
        from app.models.schemas import DetectionResult, DetectionBox

        # 查询检测结果详情
        boxes = []
        if hasattr(record, 'results') and record.results:
            for result in record.results:
                boxes.append(DetectionBox(
                    x1=result.x1,
                    y1=result.y1,
                    x2=result.x2,
                    y2=result.y2,
                    confidence=result.confidence,
                    class_id=result.class_id,
                    class_name=result.class_name,
                    chinese_name=result.chinese_name
                ))

        detection_result = DetectionResult(
            detection_id=str(record.id),
            image_url=image_url,
            result_image_url=result_url,
            video_url=video_url,
            cover_image_url=cover_url,
            boxes=boxes,
            total_objects=record.total_objects or 0,
            detection_time=record.detection_time or 0,
            model_name=record.model_name or "mab-yolo11m",
            created_at=record.created_at
        )

        return SingleDetectionResponse(
            success=True,
            message="获取成功",
            data=detection_result
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取检测记录失败: {str(e)}"
        )


# =============================================================================
# 删除检测记录接口
# =============================================================================

@router.delete("/{detection_id}")
async def delete_detection(
    detection_id: str = Path(..., description="检测记录 ID")
):
    """
    删除检测记录接口

    功能：
    - 根据检测 ID 删除数据库中的检测记录及关联数据

    参数：
        detection_id: 检测记录 ID

    返回：
        dict: 删除结果
    """
    try:
        # 调用检测服务删除检测记录
        success = detection_service.delete_detection(detection_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail="检测记录不存在"
            )

        return {
            "success": True,
            "message": "删除成功"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"删除检测记录失败: {str(e)}"
        )


# =============================================================================
# 目标类别列表接口
# =============================================================================

@router.get("/targets/list", response_model=TargetListResponse)
async def get_target_list():
    """
    获取可检测目标类别列表接口

    功能：
    - 返回系统支持检测的所有目标类别
    - MaB 数据集包含 4 种水果成熟度类别

    返回：
        TargetListResponse: 包含目标类别列表的响应

    响应示例：
        {
            "success": true,
            "message": "获取成功",
            "data": [
                {
                    "id": 0,
                    "name": "Raw_Banana",
                    "chinese_name": "未成熟香蕉",
                    "description": "处于未成熟阶段的香蕉"
                },
                ...
            ]
        }
    """
    # 定义 MaB 数据集支持检测的目标类别列表
    targets = [
        TargetItem(id=0, name="Raw_Banana", chinese_name="未成熟香蕉", description="处于未成熟阶段的香蕉"),
        TargetItem(id=1, name="Raw_Mango", chinese_name="未成熟芒果", description="处于未成熟阶段的芒果"),
        TargetItem(id=2, name="Ripe_Banana", chinese_name="成熟香蕉", description="已经成熟的香蕉"),
        TargetItem(id=3, name="Ripe_Mango", chinese_name="成熟芒果", description="已经成熟的芒果"),
    ]

    # 返回目标列表响应
    return TargetListResponse(
        success=True,              # 请求成功
        message="获取成功",         # 提示信息
        data=targets              # 目标类别列表
    )


# =============================================================================
# MinIO 文件代理接口
# =============================================================================

@router.get("/files/{bucket}/{filename}", response_class=Response)
def get_file(bucket: str, filename: str, request: Request):
    """
    MinIO 文件代理接口

    功能：
    - 从 MinIO 获取文件并返回给前端
    - 解决前端无法直接访问 MinIO 的问题

    参数：
        bucket: MinIO Bucket 名称
        filename: 文件名

    返回：
        文件流
    """
    try:
        from app.services.minio_service import minio_service
        
        # 从 MinIO 获取文件
        response = minio_service.client.get_object(bucket, filename)
        
        # 确定内容类型
        content_type = "image/jpeg"
        if filename.endswith(".png"):
            content_type = "image/png"
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
            content_type = "image/jpeg"
        elif filename.endswith(".mp4"):
            content_type = "video/mp4"
        
        # 读取所有数据
        data = response.read()
        
        # 关闭响应对象
        response.close()
        response.release_conn()
        
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="{filename}"',
        }
        range_header = request.headers.get("range")
        if range_header and range_header.startswith("bytes="):
            try:
                range_value = range_header.replace("bytes=", "", 1)
                start_text, end_text = range_value.split("-", 1)
                start = int(start_text) if start_text else 0
                end = int(end_text) if end_text else len(data) - 1
                end = min(end, len(data) - 1)
                if start < 0 or start > end or start >= len(data):
                    return Response(
                        status_code=416,
                        headers={"Content-Range": f"bytes */{len(data)}"}
                    )

                partial_data = data[start:end + 1]
                headers.update({
                    "Content-Range": f"bytes {start}-{end}/{len(data)}",
                    "Content-Length": str(len(partial_data)),
                })
                return Response(
                    content=partial_data,
                    status_code=206,
                    media_type=content_type,
                    headers=headers
                )
            except Exception:
                pass

        headers["Content-Length"] = str(len(data))
        return Response(
            content=data,
            media_type=content_type,
            headers=headers
        )
        
    except Exception as e:
        print(f"[文件代理错误] Bucket: {bucket}, Filename: {filename}")
        print(f"[文件代理错误] {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail="文件不存在或已被清理"
        )
