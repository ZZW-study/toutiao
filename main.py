import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from routers import news,users,favorite,history,chat
from utils.exception_handlers import register_exception_handlers
from middlewares.token_bucket_rate_limit import custom_rate_limit_handler
from middlewares.token_bucket_middleware import TokenBucketRateLimitMiddleware

app = FastAPI()

#跨域资源共享CORS，中间件.
#让后端主动告诉浏览器：这个前端可以访问
#允许的来源
origins = [
    "http://localhost",
    "http://localhost:5173"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,#允许访问的源
    allow_credentials = True,#允许携带Cookie
    allow_methods = ["*"],#允许所有的请求方法
    allow_headers = ["*"] #允许所有的请求头
)
app.add_middleware(TokenBucketRateLimitMiddleware)


# 注册全局异常处理器
register_exception_handlers(app)
app.add_exception_handler(RateLimitExceeded,custom_rate_limit_handler)



@app.get("/")
async def root():
    return {"msg":"Hello World"}

#挂在路由方法,news是模块对象，router是属性
app.include_router(news.router)
app.include_router(users.router)
app.include_router(favorite.router)
app.include_router(history.router)
app.include_router(chat.router)


if __name__ == "__main__":
    uvicorn.run("main:app",host="127.0.0.1",port=8000,reload=True) # 开启热重载


