# xjtlu_adapter_final.py - Fixed Session ID Test Version
import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import json
import time
import uuid
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv, find_dotenv
from datetime import datetime

# --- Configuration & Constants ---
load_dotenv(find_dotenv())

# API endpoint URLs
CREATE_SESSION_URL = "https://jmapi.xjtlu.edu.cn/api/chat/saveSession?sf_request_type=ajax"
CHAT_API_URL = "https://jmapi.xjtlu.edu.cn/api/chat/completions?sf_request_type=fetch"

# --- 日志配置 (保持不变) ---
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logger = logging.getLogger("adapter_logger")
logger.setLevel(logging.INFO)
log_filename = f"adapter_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, log_filename), 
    maxBytes=5*1024*1024, 
    backupCount=5, 
    encoding='utf-8'
)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(file_handler)

# --- FastAPI App ---
app = FastAPI(
    title="XJTLU GenAI Adapter (Fixed Session Test)",
    description="An adapter using a fixed session ID to bypass rate limiting issues."
)
client = httpx.AsyncClient(timeout=120.0)

def get_dynamic_headers():
    """Dynamically loads credentials from the .env file for each request."""
    load_dotenv(find_dotenv(), override=True)
    
    jm_token = os.getenv("JM_TOKEN")
    sdp_session = os.getenv("SDP_SESSION")

    if not jm_token or not sdp_session:
        raise ValueError("JM_TOKEN or SDP_SESSION not found in .env file.")

    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "origin": "https://xipuai.xjtlu.edu.cn",
        "referer": "https://xipuai.xjtlu.edu.cn/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "jm-token": jm_token,
        "sdp-app-session": sdp_session,
    }

# We don't need the create_new_session function for this test version, but we'll keep it for future use.
async def create_new_session(headers):
    # ... (code is here but will not be called) ...
    pass

@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    try:
        headers = get_dynamic_headers()
        openai_request = await request.json()
        logger.info(f"Received request: {json.dumps(openai_request, ensure_ascii=False, indent=2)}")
    except ValueError as e:
        logger.error(f"Credential loading error: {e}. Please run auth.py.")
        raise HTTPException(status_code=401, detail=str(e))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body.")

    messages = openai_request.get("messages", [])
    model_name = openai_request.get("model", "")
    
    # ==================== KEY CHANGE ====================
    # For testing purposes, we will hardcode the session ID to a known, valid one.
    # This bypasses the session creation logic entirely.
    session_id = "68187"
    logger.info(f"Using FIXED Session ID for this request: {session_id}")
    # ======================================================

    user_prompt = messages[-1].get("content", "")
    xjtlu_payload = {"text": user_prompt, "files": [], "sessionId": session_id}

    async def stream_generator():
        logger.info(f"Streaming request to upstream for FIXED Session ID: {session_id}")
        try:
            async with client.stream("POST", CHAT_API_URL, json=xjtlu_payload, headers=headers) as response:
                if response.status_code != 200:
                    error_content = await response.aread()
                    logger.error(f"Upstream API error ({response.status_code}): {error_content.decode()}")
                    error_chunk = {"error": {"message": f"Upstream API error: {error_content.decode()}", "type": "upstream_error", "code": response.status_code}}
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    return

                logger.info(f"Upstream response successful. Processing stream...")
                first_chunk = True
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        chunk_str = line[len("data:"):].strip()
                        if not chunk_str or chunk_str == "[DONE]":
                            continue

                        try:
                            xjtlu_chunk = json.loads(chunk_str)
                            data_content = xjtlu_chunk.get("data")
                            
                            if not isinstance(data_content, str):
                                logger.warning(f"Skipping non-text data chunk: {data_content}")
                                continue
                            
                            # On the first chunk, we can still report the model name with the fixed session ID
                            model_to_return = f"xjtlu-genai:session:{session_id}" if first_chunk else model_name
                            first_chunk = False
                            
                            openai_chunk = {
                                "id": f"chatcmpl-{uuid.uuid4()}",
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model_to_return,
                                "choices": [{"index": 0, "delta": {"content": data_content}, "finish_reason": None}]
                            }
                            yield f"data: {json.dumps(openai_chunk)}\n\n"
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping non-JSON data chunk: '{chunk_str}'")
                
                # Send the final [DONE] message
                done_chunk = {
                    "id": f"chatcmpl-{uuid.uuid4()}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model_name,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(done_chunk)}\n\n"
                yield "data: [DONE]\n\n"
                logger.info(f"Stream finished for FIXED Session ID: {session_id}")

        except httpx.RequestError as e:
            logger.error(f"Network error during streaming request: {e}", exc_info=True)
            error_chunk = {"error": {"message": f"Network error: {e}", "type": "network_error"}}
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"
            
    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@app.get("/", include_in_schema=False)
def root():
    return {"message": "XJTLU GenAI Adapter is running in fixed-session test mode.", "status": "ok"}

# --- Startup/Shutdown Events (保持不变) ---
@app.on_event("startup")
async def startup_event():
    logger.info("Starting XJTLU GenAI Adapter (Fixed Session Test Mode)...")
    if not os.getenv("JM_TOKEN") or not os.getenv("SDP_SESSION"):
        logger.warning("JM_TOKEN or SDP_SESSION not found. Please run auth.py to fetch them.")
    else:
        logger.info("Credentials found in .env file.")

@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()
    logger.info("Adapter shut down.")