def generate_repr(obj):
    """
    通用的 __repr__ 内容生成函数
    :param obj: 类的实例对象（self）
    :return: 标准化的 repr 字符串
    """
    # 针对 SQLAlchemy 模型：提取表的所有列名和对应值
    if hasattr(obj, '__table__'):
        attrs = [f"{col.name}={getattr(obj,col.name)!r}" for col in obj.__table__.columns]
        # join() 是 Python 字符串的内置方法，核心功能是：
        # 将一个包含字符串元素的可迭代对象（列表、元组、生成器等），用调用 join() 的字符串作为「分隔符」，拼接成一个新的完整字符串。
        attrs_str = ", ".join(attrs)
        return f"<{obj.__class__.__name__}({attrs_str})>"
    # 通用场景（非 SQLAlchemy 模型）：提取实例的所有属性
    else:
        attrs = [f"{k}={v!r}" for k, v in obj.__dict__.items() if not k.startswith('_')]
        attrs_str = ", ".join(attrs)
        return f"<{obj.__class__.__name__}({attrs_str})>"




