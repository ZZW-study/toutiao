# 故封装通用的响应格式，在路由函数中，直接调用即可，不用每次都写相同的响应格式
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

def success_response(message : str="success", data=None):
    content = {
        "code": 200,
        "message": message,
        "data": data
        }
# FastAPI 默认会自动将返回值转为 JSON，但在需要自定义响应（比如修改状态码、添加响应头、定制 JSON 结构）时，就需要显式使用 JSONResponse。
# jsonable_encoder是将 Python 非标准类型（如 datetime、Pydantic 模型、UUID 等）转换为 JSON 可序列化的基础类型（str、int、dict 等）。
    return JSONResponse(content=jsonable_encoder(content))










