# -*- coding: utf-8 -*-
"""缓存实现测试。"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

from pydantic import BaseModel  # 从 pydantic 模块导入当前文件后续要用到的对象

from cache.local_cache import LocalLRUCache  # 从 cache.local_cache 模块导入当前文件后续要用到的对象
from cache.redis_cache import generate_cache_key  # 从 cache.redis_cache 模块导入当前文件后续要用到的对象


class _QueryModel(BaseModel):  # 定义 _QueryModel 类，用来把这一块相关的状态和行为组织在一起
    """用于模拟结构化查询参数，验证缓存 key 生成是否稳定。"""
    category_id: int  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    page: int  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行


def test_generate_cache_key_is_stable_for_kwarg_order():  # 定义函数 test_generate_cache_key_is_stable_for_kwarg_order，把一段可以复用的逻辑单独封装起来
    """关键字参数顺序不同也应生成相同 key。"""

    key1 = generate_cache_key("news:list", args=(), kwargs={"page": 1, "category_id": 7})  # 把右边计算出来的结果保存到 key1 变量中，方便后面的代码继续复用
    key2 = generate_cache_key("news:list", args=(), kwargs={"category_id": 7, "page": 1})  # 把右边计算出来的结果保存到 key2 变量中，方便后面的代码继续复用
    assert key1 == key2  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


def test_generate_cache_key_distinguishes_structured_args():  # 定义函数 test_generate_cache_key_distinguishes_structured_args，把一段可以复用的逻辑单独封装起来
    """结构化参数不同必须生成不同 key。"""

    key1 = generate_cache_key("news:list", args=(_QueryModel(category_id=7, page=1),), kwargs={})  # 把右边计算出来的结果保存到 key1 变量中，方便后面的代码继续复用
    key2 = generate_cache_key("news:list", args=(_QueryModel(category_id=7, page=2),), kwargs={})  # 把右边计算出来的结果保存到 key2 变量中，方便后面的代码继续复用
    assert key1 != key2  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


def test_local_cache_distinguishes_miss_and_empty_hit():  # 定义函数 test_local_cache_distinguishes_miss_and_empty_hit，把一段可以复用的逻辑单独封装起来
    """本地缓存要能区分未命中与负缓存命中。"""

    cache = LocalLRUCache(maxsize=10, ttl=60)  # 把右边计算出来的结果保存到 cache 变量中，方便后面的代码继续复用

    miss = cache.get_entry("missing")  # 把右边计算出来的结果保存到 miss 变量中，方便后面的代码继续复用
    assert miss.hit is False  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert miss.value is None  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题

    cache.set("missing", None)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    empty_hit = cache.get_entry("missing")  # 把右边计算出来的结果保存到 empty_hit 变量中，方便后面的代码继续复用
    assert empty_hit.hit is True  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert empty_hit.value is None  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
