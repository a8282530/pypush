# coding: utf-8
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from app import userlogin, encrypt, decrypt
from imessage import iMessageUser, iMessage
from requests import get
from uvicorn import run
from datetime import datetime
import time
import json
import asyncio

user_list = {}

app = FastAPI(
    title='docker',
    version='1.0.0',
    description='docker api',
    debug=True
)

app.add_middleware(
    CORSMiddleware,
    # 允许跨域的源列表，例如 ["http://www.example.org"] 等等，["*"] 表示允许任何源
    allow_origins=["*"],
    # 跨域请求是否支持 cookie，默认是 False，如果为 True，allow_origins 必须为具体的源，不可以是 ["*"]
    allow_credentials=False,
    # 允许跨域请求的 HTTP 方法列表，默认是 ["GET"]
    allow_methods=["*"],
    # 允许跨域请求的 HTTP 请求头列表，默认是 []，可以使用 ["*"] 表示允许所有的请求头
    # 当然 Accept、Accept-Language、Content-Language 以及 Content-Type 总之被允许的
    allow_headers=["*"],
    # 可以被浏览器访问的响应头, 默认是 []，一般很少指定
    # expose_headers=["*"]
    # 设定浏览器缓存 CORS 响应的最长时间，单位是秒。默认为 600，一般也很少指定
    # max_age=1000
)


def query_ip():
    try:
        res = get('http://ip-api.com/json', timeout=10)
        result = res.json()
        return result.get('query', 'docker.ip')
    except Exception:
        return 'timeout'


# 获取当前时间，并转换为 JSON 格式
def get_time_json():
    dt_ms = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    return json.dumps({'time': dt_ms}, ensure_ascii=False)


@app.get('/')
def index():
    ip = query_ip()
    return {'ip': ip}


@app.post('/login')
async def login(request: Request):
    params = await request.json()
    user = params.get('user')
    pwd = params.get('pwd')

    result = {
        'status': 'login error',
        'user': user
    }
    if not (user and pwd):
        return result
    try:
        user, pwd = user.strip(), pwd.strip()
        users = userlogin(user, pwd)
        token = encrypt(user)
        result |= {
            'status': 'success',
            'token': token
        }
        print(token)
        user_list.update({user: {'users': users, 'im': None}})
    except Exception:
        result |= {
            'status': 'username or password error'
        }
    # im = iMessageUser(users)
    # print(im)
    return result

@app.post('/lookup')
async def lookup(request: Request):
    params = await request.json()
    contacts = params.get('contacts') # 联系人
    token = params.get('token')
    result = {
        'status': 'error',
        'token': token
    }
    if not (contacts and token):
        return result
    try:
        contacts = f'mailto:{contacts}' if '@' in contacts else f'tel:{contacts}'
        target = user_list.get(decrypt(token))
        _, user = target.get('users')
        res = user.lookup([contacts])  
        print(res, contacts)
        data = list(filter(lambda x:res.get(x, {}).get('sender-correlation-identifier'), [contacts]))
        result |= {
            'status': res.get('status') or 'success',
            'result': data
        }
    except Exception:
        pass
    return result

@app.post('/sendmsg')
async def sendmsg(request: Request):
    params = await request.json()
    msg = params.get('msg')
    sender = params.get('sender')
    effect = params.get('effect')
    token = params.get('token')
    result = {
        'status': 'error',
        'token': token
    }
    if not (msg and sender and token):
        return result
    sender = f'mailto:{sender}' if '@' in sender else f'tel:{sender}'
    try:
        target = user_list.get(decrypt(token))
        conn, user = target.get('users')
        im = target.get('im')
        print(conn,user, im, user.current_handle)
        status = im.send(iMessage(
            text=msg,
            participants=[sender],
            sender=user.current_handle,
            effect=effect
        ))
        result['status'] = status
    except Exception:
        pass
    return result

@app.get('/receive')
async def receive(request: Request, token: str):
    im = None
    async def event_generator(im: iMessageUser):
        n = 1
        retry_time = 5000

        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break
            if not im:
                break
            msg = im.receive()
            if msg is not None:
                msg_content = {
                    "msg": msg.text,
                    "sender": msg.sender,
                    "effect": msg.effect or ""
                }
                yield {
                    "event": "receive",
                    "id": f"{n}",
                    "retry": retry_time,
                    "data": json.dumps(msg_content, ensure_ascii=False)
                }
                n += 1
            await asyncio.sleep(0.1)
        yield {
            "event": "unauthorized",
            "id": "0",
            "retry": retry_time,
            "data": "token is not found"
        }

    try:
        target = user_list.get(decrypt(token))
        conn, user = target.get('users')
        im = iMessageUser(conn, user)
        target['im'] = im
    except Exception:
        pass
    return EventSourceResponse(event_generator(im))


@app.get("/test")
def test(request: Request):
    headers = {
        'Content-type': 'text/event-stream',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache, no-transform',
        'X-Accel-Buffering': 'no'
    }

    def event(request: Request):
        n = 1
        while True:
            msg_content = {
                "msg": "hello",
                "sender": "msg.sender.com",
                "effect": ""
            }
            yield f'id: {n}\nevent: receive\nretry: 5000\ndata: {json.dumps(msg_content, ensure_ascii=False)}\n\n'
            n += 1
            time.sleep(5.1)
    return StreamingResponse(content=event(request), headers=headers)


@app.get('/stream')
async def message_stream(request: Request):
    def new_messages():
        # Add logic here to check for new messages
        yield 'Hello World'

    async def event_generator():
        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break

            # Checks for new messages and return them to client if any
            if new_messages():
                yield {
                    "event": "new_message",
                    "id": "message_id",
                    "retry": 15000,
                    "data": "message_content"
                }

            await asyncio.sleep(5)

    return EventSourceResponse(event_generator())

if __name__ == '__main__':
    run(app='main:app', host='0.0.0.0', port=1080,  reload=True)
