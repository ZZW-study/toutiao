# -*- coding: utf-8 -*-
"""
密码安全模块
使用 bcrypt 进行密码哈希和验证
"""
from passlib.context import CryptContext

# 配置 bcrypt 密码哈希上下文
# bcrypt 是专门为密码存储设计的哈希算法，具有以下优势：
# 1. 内置盐值，防止彩虹表攻击
# 2. 计算成本可调，抵抗暴力破解
# 3. 业界标准，广泛使用
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hash_password(password: str) -> str:
    """
    生成密码的 bcrypt 哈希值
    :param password: 明文密码
    :return: 哈希后的密码字符串
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希值是否匹配
    :param plain_password: 明文密码
    :param hashed_password: 哈希后的密码
    :return: 是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)
