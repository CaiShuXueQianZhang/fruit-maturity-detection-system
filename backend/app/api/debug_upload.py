from fastapi import APIRouter, UploadFile, File, Request
from typing import List

router = APIRouter()


@router.post("/debug/upload")
async def debug_upload(request: Request, files: List[UploadFile] = File(None)):
    """
    调试用上传接口：不依赖模型，直接返回接收到的文件数量与文件名列表
    用于快速确认前端是否正确发送了多文件 multipart/form-data 请求
    """
    parsed_files = []
    if files:
        parsed_files = files
    else:
        form = await request.form()
        for v in form.values():
            if isinstance(v, UploadFile):
                parsed_files.append(v)

    names = [f.filename for f in parsed_files]
    return {"received": len(parsed_files), "filenames": names}
