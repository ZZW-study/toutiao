# -*- coding: utf-8 -*-
"""缓存实现测试。"""

from __future__ import annotations

from pydantic import BaseModel

from cache.local_cache import LocalLRUCache
from cache.redis_cache import generate_cache_key


class _QueryModel(BaseModel):
    """用于模拟结构化查询参数，验证缓存 key 生成是否稳定。"""
    category_id: int
    page: int


def test_generate_cache_key_is_stable_for_kwarg_order():
    """关键字参数顺序不同也应生成相同 key。"""

    key1 = generate_cache_key("news:list", args=(), kwargs={"page": 1, "category_id": 7})
    key2 = generate_cache_key("news:list", args=(), kwargs={"category_id": 7, "page": 1})
    assert key1 == key2


def test_generate_cache_key_distinguishes_structured_args():
    """结构化参数不同必须生成不同 key。"""

    key1 = generate_cache_key("news:list", args=(_QueryModel(category_id=7, page=1),), kwargs={})
    key2 = generate_cache_key("news:list", args=(_QueryModel(category_id=7, page=2),), kwargs={})
    assert key1 != key2


def test_local_cache_distinguishes_miss_and_empty_hit():
    """本地缓存要能区分未命中与负缓存命中。"""

    cache = LocalLRUCache(maxsize=10, ttl=60)

    miss = cache.get_entry("missing")
    assert miss.hit is False
    assert miss.value is None

    cache.set("missing", None)
    empty_hit = cache.get_entry("missing")
    assert empty_hit.hit is True
    assert empty_hit.value is None
