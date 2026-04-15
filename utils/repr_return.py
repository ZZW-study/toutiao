"""统一生成对象的 `__repr__` 字符串。

`__repr__` 的主要用途不是给用户看，而是给开发者调试时看。
当你在日志、断点或者交互式终端里打印对象时，
一个清晰的 `__repr__` 能让你立刻知道对象里到底装了什么数据。
"""

from __future__ import annotations


def generate_repr(obj):
    """返回适合调试的字符串表示。

    处理策略分两种：
    1. 如果对象是 SQLAlchemy 模型，就按数据库列顺序提取字段。
    2. 如果是普通 Python 对象，就从 `__dict__` 中提取公开属性。
    """

    if hasattr(obj, "__table__"):
        attrs = [f"{col.name}={getattr(obj, col.name)!r}" for col in obj.__table__.columns]
        attrs_str = ", ".join(attrs)
        return f"<{obj.__class__.__name__}({attrs_str})>"

    attrs = [f"{key}={value!r}" for key, value in obj.__dict__.items() if not key.startswith("_")]
    attrs_str = ", ".join(attrs)
    return f"<{obj.__class__.__name__}({attrs_str})>"
