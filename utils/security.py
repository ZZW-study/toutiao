# -*- coding: utf-8 -*-
"""密码安全模块，使用 bcrypt 进行密码哈希和验证。"""

from passlib.context import CryptContext

# bcrypt 配置：内置盐值、计算成本可调、业界标准
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hash_password(password: str) -> str:
    """生成密码的 bcrypt 哈希值。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希值是否匹配。"""
    return pwd_context.verify(plain_password, hashed_password)
