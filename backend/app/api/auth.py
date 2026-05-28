"""
认证 API 路由

提供：
- POST /api/auth/register  注册
- POST /api/auth/login     登录，返回 session token
- GET  /api/auth/me        获取当前用户信息（需 Authorization: Bearer <token>）
- POST /api/auth/logout    登出（删除会话）

实现说明：使用数据库中的 `User` 表验证密码（PBKDF2），会话使用 Redis 存储。
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.database import get_db, User
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_session,
    get_userid_by_session,
    delete_session,
)

router = APIRouter(prefix="/auth", tags=["auth"]) 


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: str = Field(..., min_length=5, max_length=100, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=6, max_length=64)
    nickname: Optional[str] = Field(None, max_length=50)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=64)


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    nickname: Optional[str] = None
    role: Optional[str] = None
    avatar_url: Optional[str] = None


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[UserOut] = None


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        nickname=getattr(user, "nickname", None),
        role=getattr(user, "role", None),
        avatar_url=getattr(user, "avatar_url", None),
    )


def _create_login_response(user: User, message: str) -> LoginResponse:
    token = create_session(user.id)
    if not token:
        raise HTTPException(status_code=500, detail="登录会话创建失败，请稍后重试")
    return LoginResponse(success=True, message=message, token=token, user=_to_user_out(user))


@router.post("/register", response_model=LoginResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """注册新用户，成功后直接返回登录会话。"""
    username = req.username.strip()
    email = req.email.lower().strip()
    nickname = req.nickname.strip() if req.nickname else None

    try:
        exists = db.query(User).filter(or_(User.username == username, User.email == email)).first()
    except Exception:
        raise HTTPException(status_code=500, detail="数据库不可用")

    if exists:
        raise HTTPException(status_code=400, detail="用户名或邮箱已存在")

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(req.password),
        nickname=nickname,
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建用户失败: {e}")

    return _create_login_response(user, "注册成功")


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """使用用户名或邮箱登录，返回 session token（存在 Redis）"""
    account = req.username.strip()
    email_account = account.lower()

    try:
        user = db.query(User).filter(or_(User.username == account, User.email == email_account)).first()
    except Exception:
        raise HTTPException(status_code=500, detail="数据库查询失败")

    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not verify_password(user.password_hash, req.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if getattr(user, "is_active", True) is False:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    return _create_login_response(user, "登录成功")


def _extract_token_from_header(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return auth


@router.get("/me", response_model=UserOut)
def me(request: Request, db: Session = Depends(get_db)):
    token = _extract_token_from_header(request)
    if not token:
        raise HTTPException(status_code=401, detail="未提供认证信息")

    user_id = get_userid_by_session(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="会话无效或已过期")

    try:
        user = db.query(User).filter(User.id == user_id).first()
    except Exception:
        raise HTTPException(status_code=500, detail="数据库查询失败")

    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return _to_user_out(user)


@router.post("/logout")
def logout(request: Request):
    token = _extract_token_from_header(request)
    if not token:
        return {"success": True, "message": "已登出"}
    delete_session(token)
    return {"success": True, "message": "已登出"}
