# xjtlu_adapter_final_v11.py - Definitive Version with Truncation Logic & Debug Mode
import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import json
import time
import uuid
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
import asyncio

# --- Configuration ---
load_dotenv(find_dotenv())
BASE_URL = "https://jmapi.xjtlu.edu.cn/api/chat"
SESSION_API_URL = f"{BASE_URL}/saveSession?sf_request_type=ajax"
CHAT_API_URL = f"{BASE_URL}/completions?sf_request_type=fetch"
DELETE_SESSION_URL = f"{BASE_URL}/delSession?sf_request_type=ajax"

# --- Tweakable Parameters ---
# This delay is CRITICAL to avoid "request too fast" errors.
INTER_REQUEST_DELAY = 1.0 
# The character limit for a single content block before truncation.
# This logic proved to be the key to handling large, complex RAG inputs.
MAX_CONTENT_LENGTH = 1500 # Slightly increased, but still active.
# ===================================================================
# ==                 调试开关：自动删除功能已屏蔽                  ==
# ==    将此值改为 True 即可重新启用“完成对话后自动删除会话”功能   ==
# ===================================================================
ENABLE_AUTO_DELETION = False

AVAILABLE_MODELS = [
    "DeepSeek-R1", "DeepseekR1联网", "qwen-2.5-72b", "gpt-4.1-nano", "gpt-4.1",
    "o1-mini", "o3-mini", "gpt-o3", "o4-mini", "gemini-2.5-pro-exp-03-25",
    "claude-3-7-sonnet-20250219",
]

# --- Logging Setup ---
# (此部分保持不变)
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

# --- FastAPI App & Helper Functions ---
app = FastAPI(
    title="XJTLU GenAI Adapter (v11 - Debug Mode)",
    description="Reinstated the successful truncation logic. Auto-deletion is disabled. This is the definitive approach."
)
client = httpx.AsyncClient(timeout=120.0)

def get_dynamic_headers():
    # (此部分保持不变)
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
    """
    **REINSTATED**: This function processes messages to truncate long content blocks
    and then formats them into a single prompt. This was accidentally the key to success.
    """
    processed_messages = []
    for msg in messages:
        content = msg.get("content", "")
        # The critical truncation logic
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

    # Use the simple and effective formatting
    prompt_parts = [f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}" for msg in processed_messages]
    full_prompt = "\n\n".join(prompt_parts)
    logger.info(f"Final, PROCESSED prompt for backend:\n---\n{full_prompt}\n---")
    return full_prompt


async def create_new_session(openai_request: dict):
    # (此部分保持不变)
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


async def delete_session(session_id: str):
    # (此部分保持不变)
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
    logger.info("Starting XJTLU GenAI Adapter (v11 - Final Debug)...")

@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()
    logger.info("Adapter shut down.")

@app.get("/v1/models")
async def list_models():
    # (此部分保持不变)
    logger.info("Received request for model list.")
    model_list = [{"id": model_id, "object": "model", "created": int(time.time()), "owned_by": "XJTLU"} for model_id in AVAILABLE_MODELS]
    return JSONResponse(content={"object": "list", "data": model_list})

@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    try:
        openai_request = await request.json()
        logger.info(f"\n--- CLIENT REQ ---\n{json.dumps(openai_request, indent=2, ensure_ascii=False)}\n------------------")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # --- Step 1: Create a new, fully configured session ---
    session_id_to_use = await create_new_session(openai_request)
    
    # --- Step 2: Process messages for length and format into a single prompt ---
    messages = openai_request.get("messages", [])
    if not messages:
        if ENABLE_AUTO_DELETION: asyncio.create_task(delete_session(session_id_to_use))
        raise HTTPException(status_code=400, detail="No 'messages' in request.")
    
    # **REINSTATED CRITICAL STEP**
    full_prompt = process_and_format_prompt(messages)
    
    # --- Step 3: Add the critical delay ---
    await asyncio.sleep(INTER_REQUEST_DELAY)

    # --- Step 4: Stream the final answer ---
    xjtlu_payload = {"text": full_prompt, "files": [], "sessionId": session_id_to_use}

    async def stream_generator():
        try:
            logger.info(f"Sending final prompt to Session ID: {session_id_to_use}")
            async with client.stream("POST", CHAT_API_URL, json=xjtlu_payload, headers=get_dynamic_headers()) as response:
                response.raise_for_status()
                # (Stream parsing logic remains the same)
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