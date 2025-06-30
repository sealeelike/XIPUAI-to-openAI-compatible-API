# xjtlu_adapter_final_v12.py - 添加心跳保活机制
import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import json
import time
import uuid
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv, find_dotenv, set_key
from datetime import datetime
import asyncio

# --- Configuration ---
load_dotenv(find_dotenv())
BASE_URL = "https://jmapi.xjtlu.edu.cn/api/chat"
SESSION_API_URL = f"{BASE_URL}/saveSession?sf_request_type=ajax"
CHAT_API_URL = f"{BASE_URL}/completions?sf_request_type=fetch"
DELETE_SESSION_URL = f"{BASE_URL}/delSession?sf_request_type=ajax"

# --- Tweakable Parameters ---
INTER_REQUEST_DELAY = 1.0 
MAX_CONTENT_LENGTH = 1500
ENABLE_AUTO_DELETION = True

# ===================================================================
# ==                    心跳保活机制配置                           ==
# ===================================================================
# 心跳间隔（秒）- 用户静默多长时间后开始发送心跳
HEARTBEAT_INTERVAL = 1200  # 20分钟，可自定义
# 是否启用心跳功能
ENABLE_HEARTBEAT = True
# 心跳会话名称
HEARTBEAT_SESSION_NAME = "Persistent Heartbeat Session"
# ===================================================================

AVAILABLE_MODELS = [
    "DeepSeek-R1", "DeepseekR1联网", "qwen-2.5-72b", "gpt-4.1-nano", "gpt-4.1",
    "o1-mini", "o3-mini", "gpt-o3", "o4-mini", "gemini-2.5-pro-exp-03-25",
    "claude-3-7-sonnet-20250219",
]

# --- Logging Setup ---
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger("adapter_logger")
logger.setLevel(logging.INFO)
log_filename = f"adapter_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
file_handler = RotatingFileHandler(os.path.join(LOG_DIR, log_filename), maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(file_handler)

# --- FastAPI App & Global Variables ---
app = FastAPI(
    title="XJTLU GenAI Adapter (v12 - With Heartbeat)",
    description="添加了心跳保活机制的适配器"
)
client = httpx.AsyncClient(timeout=120.0)

# 心跳相关全局变量
heartbeat_session_id = None
last_user_activity = time.time()
heartbeat_task = None

def get_dynamic_headers():
    load_dotenv(find_dotenv(), override=True)
    jm_token = os.getenv("JM_TOKEN")
    sdp_session = os.getenv("SDP_SESSION")
    if not jm_token or not sdp_session:
        raise ValueError("JM_TOKEN or SDP_SESSION not found in .env file.")
    return {
        "accept": "application/json, text/plain, */*", "content-type": "application/json",
        "origin": "https://xipuai.xjtlu.edu.cn", "referer": "https://xipuai.xjtlu.edu.cn/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "jm-token": jm_token, "sdp-app-session": sdp_session,
    }

def process_and_format_prompt(messages: list) -> str:
    """处理消息并截断长内容块"""
    processed_messages = []
    for msg in messages:
        content = msg.get("content", "")
        if len(content) > MAX_CONTENT_LENGTH:
            half_len = MAX_CONTENT_LENGTH // 2
            truncated_content = (
                f"{content[:half_len]}\n\n"
                f"[... Note: The middle of the preceding reference material has been truncated by the adapter due to its excessive length ...]\n\n"
                f"{content[-half_len:]}"
            )
            logger.warning(f"Content from role '{msg['role']}' was TRUNCATED from {len(content)} to {len(truncated_content)} chars.")
            processed_msg = msg.copy()
            processed_msg["content"] = truncated_content
            processed_messages.append(processed_msg)
        else:
            processed_messages.append(msg)

    prompt_parts = [f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}" for msg in processed_messages]
    full_prompt = "\n\n".join(prompt_parts)
    logger.info(f"Final, PROCESSED prompt for backend:\n---\n{full_prompt}\n---")
    return full_prompt

async def create_new_session(openai_request: dict):
    """创建新的会话"""
    headers = get_dynamic_headers()
    session_name = f"API Request @ {datetime.now().strftime('%H:%M:%S')}"
    payload = {
        "name": session_name,
        "model": openai_request.get("model"),
        "temperature": openai_request.get("temperature", 0.7),
        "maxToken": openai_request.get("max_tokens", 0),
        "presencePenalty": openai_request.get("presence_penalty", 0),
        "frequencyPenalty": openai_request.get("frequency_penalty", 0)
    }
    logger.info(f"Creating new session with payload: {json.dumps(payload)}")
    try:
        response = await client.post(SESSION_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise HTTPException(status_code=500, detail=f"Backend Error on Session Create: {data.get('msg')}")
        new_id = data.get("data", {}).get("id")
        if new_id:
            logger.info(f"✅ Successfully created new Session ID: {new_id}")
            return str(new_id)
        raise HTTPException(status_code=500, detail="Session created but no ID was returned.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Upstream API error during session creation: {e.response.text}")

async def create_heartbeat_session():
    """创建或获取心跳会话"""
    global heartbeat_session_id
    
    # 先尝试从 .env 文件读取现有的心跳会话ID
    env_file = find_dotenv()
    load_dotenv(env_file, override=True)
    existing_heartbeat_id = os.getenv("HEARTBEAT_SESSION_ID")
    
    if existing_heartbeat_id:
        logger.info(f"💓 Found existing heartbeat session ID: {existing_heartbeat_id}")
        heartbeat_session_id = existing_heartbeat_id
        return existing_heartbeat_id
    
    # 创建新的心跳会话
    headers = get_dynamic_headers()
    payload = {
        "name": HEARTBEAT_SESSION_NAME,
        "model": "qwen-2.5-72b",  # 使用默认模型
        "temperature": 0.7,
        "maxToken": 0,
        "presencePenalty": 0,
        "frequencyPenalty": 0
    }
    
    try:
        response = await client.post(SESSION_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            logger.error(f"Failed to create heartbeat session: {data.get('msg')}")
            return None
        
        new_id = data.get("data", {}).get("id")
        if new_id:
            heartbeat_session_id = str(new_id)
            # 保存到 .env 文件
            set_key(env_file, "HEARTBEAT_SESSION_ID", heartbeat_session_id)
            logger.info(f"💓 Created new heartbeat session ID: {heartbeat_session_id}")
            print(f"💓 [HEARTBEAT] Created persistent session ID: {heartbeat_session_id}")
            return heartbeat_session_id
        else:
            logger.error("Heartbeat session created but no ID was returned.")
            return None
    except Exception as e:
        logger.error(f"Failed to create heartbeat session: {e}", exc_info=True)
        return None

async def send_heartbeat():
    """发送心跳请求"""
    global heartbeat_session_id
    
    if not heartbeat_session_id:
        logger.warning("No heartbeat session ID available, attempting to create one...")
        await create_heartbeat_session()
        if not heartbeat_session_id:
            logger.error("Failed to create heartbeat session, skipping heartbeat")
            return
    
    try:
        headers = get_dynamic_headers()
        # 发送一个简单的saveSession请求作为心跳
        payload = {
            "name": HEARTBEAT_SESSION_NAME,
            "model": "qwen-2.5-72b",
            "temperature": 0.7,
            "maxToken": 0,
            "presencePenalty": 0,
            "frequencyPenalty": 0
        }
        
        response = await client.post(SESSION_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 0:
            current_time = datetime.now().strftime('%H:%M:%S')
            logger.info(f"💓 Heartbeat sent successfully at {current_time}")
            print(f"💓 [HEARTBEAT] Keepalive sent at {current_time} (Session: {heartbeat_session_id})")
        else:
            logger.warning(f"Heartbeat response warning: {data.get('msg')}")
            
    except Exception as e:
        logger.error(f"Failed to send heartbeat: {e}", exc_info=True)
        print(f"❌ [HEARTBEAT] Failed to send keepalive: {e}")

def update_user_activity():
    """更新用户活动时间"""
    global last_user_activity
    last_user_activity = time.time()

async def heartbeat_loop():
    """心跳循环任务"""
    global last_user_activity
    
    logger.info(f"💓 Heartbeat loop started (interval: {HEARTBEAT_INTERVAL}s)")
    print(f"💓 [HEARTBEAT] Keepalive enabled (interval: {HEARTBEAT_INTERVAL}s)")
    
    while True:
        try:
            await asyncio.sleep(30)  # 每30秒检查一次
            
            current_time = time.time()
            time_since_activity = current_time - last_user_activity
            
            # 如果用户静默时间超过心跳间隔，发送心跳
            if time_since_activity >= HEARTBEAT_INTERVAL:
                await send_heartbeat()
                last_user_activity = current_time  # 重置计时器
                
        except asyncio.CancelledError:
            logger.info("💓 Heartbeat loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}", exc_info=True)

async def delete_session(session_id: str):
    """删除会话（心跳会话除外）"""
    # 如果是心跳会话，不删除
    if session_id == heartbeat_session_id:
        logger.info(f"Skipping deletion of heartbeat session: {session_id}")
        return
        
    await asyncio.sleep(2.0)
    try:
        headers = get_dynamic_headers()
        payload = {"ids": [int(session_id)]}
        logger.info(f"Cleanup Task: Deleting session {session_id}...")
        response = await client.post(DELETE_SESSION_URL, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"✅ Cleanup Task: Session {session_id} deleted successfully.")
    except Exception as e:
        logger.error(f"Cleanup Task: Failed to delete session {session_id}. Error: {e}", exc_info=True)

@app.on_event("startup")
async def startup_event():
    global heartbeat_task
    
    logger.info("Starting XJTLU GenAI Adapter (v12 - With Heartbeat)...")
    print("🚀 XJTLU GenAI Adapter v12 Starting...")
    print(f"⚙️  Auto-deletion: {'Enabled' if ENABLE_AUTO_DELETION else 'Disabled'}")
    print(f"💓 Heartbeat: {'Enabled' if ENABLE_HEARTBEAT else 'Disabled'}")
    
    if ENABLE_HEARTBEAT:
        # 创建心跳会话
        await create_heartbeat_session()
        # 启动心跳任务
        heartbeat_task = asyncio.create_task(heartbeat_loop())

@app.on_event("shutdown")
async def shutdown_event():
    global heartbeat_task
    
    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
    
    await client.aclose()
    logger.info("Adapter shut down.")
    print("👋 Adapter shut down.")

@app.get("/v1/models")
async def list_models():
    update_user_activity()  # 记录用户活动
    logger.info("Received request for model list.")
    model_list = [{"id": model_id, "object": "model", "created": int(time.time()), "owned_by": "XJTLU"} for model_id in AVAILABLE_MODELS]
    return JSONResponse(content={"object": "list", "data": model_list})

@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    update_user_activity()  # 记录用户活动
    
    try:
        openai_request = await request.json()
        logger.info(f"\n--- CLIENT REQ ---\n{json.dumps(openai_request, indent=2, ensure_ascii=False)}\n------------------")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Step 1: Create a new, fully configured session
    session_id_to_use = await create_new_session(openai_request)
    
    # Step 2: Process messages for length and format into a single prompt
    messages = openai_request.get("messages", [])
    if not messages:
        if ENABLE_AUTO_DELETION: asyncio.create_task(delete_session(session_id_to_use))
        raise HTTPException(status_code=400, detail="No 'messages' in request.")
    
    full_prompt = process_and_format_prompt(messages)
    
    # Step 3: Add the critical delay
    await asyncio.sleep(INTER_REQUEST_DELAY)

    # Step 4: Stream the final answer
    xjtlu_payload = {"text": full_prompt, "files": [], "sessionId": session_id_to_use}

    async def stream_generator():
        try:
            logger.info(f"Sending final prompt to Session ID: {session_id_to_use}")
            async with client.stream("POST", CHAT_API_URL, json=xjtlu_payload, headers=get_dynamic_headers()) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        chunk_str = line[len("data:"):].strip()
                        if not chunk_str or chunk_str == "[DONE]": continue
                        try:
                            xjtlu_chunk = json.loads(chunk_str)
                            data_content = xjtlu_chunk.get("data")
                            if not isinstance(data_content, str): continue
                            openai_chunk = {"id": f"chatcmpl-{uuid.uuid4()}", "object": "chat.completion.chunk", "created": int(time.time()), "model": openai_request.get("model"), "choices": [{"index": 0, "delta": {"content": data_content}, "finish_reason": None}]}
                            yield f"data: {json.dumps(openai_chunk)}\n\n"
                        except json.JSONDecodeError: continue
                done_chunk = {"id": f"chatcmpl-{uuid.uuid4()}", "object": "chat.completion.chunk", "created": int(time.time()), "model": openai_request.get("model"), "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                yield f"data: {json.dumps(done_chunk)}\n\n"
                yield "data: [DONE]\n\n"
                logger.info(f"Stream finished for Session ID: {session_id_to_use}.")
        finally:
            # Step 5: Cleanup (respecting the debug switch)
            if ENABLE_AUTO_DELETION:
                logger.info(f"Request for session {session_id_to_use} is complete. Scheduling for deletion.")
                asyncio.create_task(delete_session(session_id_to_use))
            else:
                logger.info(f"Request for session {session_id_to_use} is complete. Auto-deletion is DISABLED for debugging.")
            
    return StreamingResponse(stream_generator(), media_type="text/event-stream")

# 添加心跳状态查询端点
@app.get("/heartbeat/status")
async def heartbeat_status():
    """查询心跳状态"""
    global heartbeat_session_id, last_user_activity
    
    return {
        "enabled": ENABLE_HEARTBEAT,
        "interval": HEARTBEAT_INTERVAL,
        "session_id": heartbeat_session_id,
        "last_activity": datetime.fromtimestamp(last_user_activity).strftime('%Y-%m-%d %H:%M:%S'),
        "time_since_activity": int(time.time() - last_user_activity)
    }
