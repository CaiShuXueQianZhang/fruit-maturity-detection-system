"""
简单认证服务：提供密码哈希/校验与会话管理（基于 Redis）

说明：使用 PBKDF2-HMAC-SHA256 对密码进行哈希，不依赖第三方密码库。
会话通过已有的 `redis_service` 存储（键格式 session:{session_id} -> user_id）。
"""
import hashlib
import hmac
import binascii
import secrets
import time
from typing import Optional

from app.services.redis_service import redis_service

# PBKDF2 配置
_SALT_BYTES = 16
_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """返回格式：pbkdf2_sha256$<iterations>$<salt_hex>$<derived_key_hex>"""
    salt = secrets.token_bytes(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"


def verify_password(stored: str, password: str) -> bool:
    try:
        parts = stored.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
            iterations = int(parts[1])
            salt_hex = parts[2]
            dk_hex = parts[3]
        elif len(parts) == 2:
            # 兼容旧格式：<salt_hex>$<derived_key_hex>
            iterations = _ITERATIONS
            salt_hex, dk_hex = parts
        else:
            return False
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(dk_hex)
    except Exception:
        return False
    new_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(new_dk, expected)


def create_session(user_id: str, expire: int = 7200) -> Optional[str]:
    """生成 session id 并保存到 Redis，返回 session_id（或 None）。"""
    session_id = secrets.token_urlsafe(32)
    # 优先使用 Redis
    try:
        ok = redis_service.set_session(session_id, user_id, expire)
        if ok:
            return session_id
    except Exception:
        pass

    # Redis 不可用时回退到进程内存（仅用于本地开发/测试）
    try:
        _IN_MEMORY_SESSIONS[session_id] = (user_id, time.time() + expire)
        return session_id
    except Exception:
        return None


def get_userid_by_session(session_id: str) -> Optional[str]:
    # 优先从 Redis 获取
    try:
        val = redis_service.get_session(session_id)
        if val:
            return val
    except Exception:
        pass

    # 回退到内存存储
    info = _IN_MEMORY_SESSIONS.get(session_id)
    if not info:
        return None
    user_id, expire_ts = info
    if expire_ts and time.time() > expire_ts:
        try:
            del _IN_MEMORY_SESSIONS[session_id]
        except Exception:
            pass
        return None
    return user_id


def delete_session(session_id: str) -> bool:
    ok = False
    try:
        redis_service.delete_session(session_id)
        ok = True
    except Exception:
        ok = False

    # 删除内存回退存储
    try:
        if session_id in _IN_MEMORY_SESSIONS:
            del _IN_MEMORY_SESSIONS[session_id]
            ok = True
    except Exception:
        pass

    return ok


# 进程内存回退会话存储（session_id -> (user_id, expire_ts)）
_IN_MEMORY_SESSIONS = {}
