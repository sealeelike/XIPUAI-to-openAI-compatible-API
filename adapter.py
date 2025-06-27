# xjtlu_adapter_final_v3.2.py - Asynchronous Pre-fetch with Full Context Reconstruction
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
SESSION_API_URL = "https://jmapi.xjtlu.edu.cn/api/chat/saveSession?sf_request_type=ajax"
CHAT_API_URL = "https://jmapi.xjtlu.edu.cn/api/chat/completions?sf_request_type=fetch"

# --- Model Configuration ---
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

# --- "Ammo" (Session ID) Management ---
session_id_ammo_box = asyncio.Queue(maxsize=1)

# --- FastAPI App & Helper Functions ---
app = FastAPI(
    title="XJTLU GenAI Adapter (Full Context Reconstruction)",
    description="Correctly handles full conversation history from stateless clients by flattening it into a single prompt."
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

async def replenish_session_id_ammo():
    # (此部分保持不变)
    await asyncio.sleep(2) 
    try:
        headers = get_dynamic_headers()
        new_chat_name = f"API Pre-fetch Standby @ {datetime.now().strftime('%H:%M:%S')}"
        payload = {"name": new_chat_name}
        logger.info(f"Replenishing ammo: Requesting new session with name '{new_chat_name}'...")
        response = await client.post(SESSION_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        new_id = data.get("data", {}).get("id")
        if new_id:
            await session_id_ammo_box.put(str(new_id))
            logger.info(f"✅ Ammo replenished. New Session ID {new_id} is ready for the next request.")
        else:
            logger.error(f"Failed to get new session ID from upstream response: {data}")
    except Exception as e:
        logger.error(f"❌ Critical error during ammo replenishment: {e}", exc_info=True)

# **** THIS IS THE CRITICAL CHANGE ****
def reconstruct_prompt_from_messages(messages: list) -> str:
    """
    Takes a list of message objects (like OpenAI's) and flattens them
    into a single, human-readable string that preserves the entire context.
    This is for backends that expect a single text prompt but need full history.
    """
    prompt_parts = []
    for message in messages:
        # System prompts might not have a role, or have a 'system' role. Handle them.
        role = message.get("role", "system").capitalize()
        content = message.get("content", "")

        # For system messages, we can just add the content. For others, show the role.
        if role == "System":
             prompt_parts.append(content)
        else:
             prompt_parts.append(f"{role}: {content}")
    
    # Join all parts with double newlines to create a clear conversational flow
    full_prompt = "\n\n".join(prompt_parts)
    return full_prompt

@app.on_event("startup")
async def startup_event():
    logger.info("Starting XJTLU GenAI Adapter with 'Full Context Reconstruction'...")
    asyncio.create_task(replenish_session_id_ammo())

@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()
    logger.info("Adapter shut down.")

@app.get("/v1/models")
async def list_models():
    # (此部分保持不变)
    logger.info("Received request for model list.")
    model_list = [
        {"id": model_id, "object": "model", "created": int(time.time()), "owned_by": "XJTLU"} 
        for model_id in AVAILABLE_MODELS
    ]
    return JSONResponse(content={"object": "list", "data": model_list})

@app.post("/v1/chat/completions")
async def chat_proxy(request: Request):
    try:
        openai_request = await request.json()
        logger.info(f"\n--- CLIENT REQ ---\n{json.dumps(openai_request, indent=2, ensure_ascii=False)}\n------------------")
        headers = get_dynamic_headers()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # --- Step 1 & 2 remain the same: Get ID, Rename, Update Params ---
    try:
        session_id_to_use = await asyncio.wait_for(session_id_ammo_box.get(), timeout=15.0)
        logger.info(f"✅ Using pre-fetched Session ID: {session_id_to_use}")

        model_to_use = openai_request.get("model")
        temperature_to_use = openai_request.get("temperature")
        new_session_name = f"API Service Session {session_id_to_use}"
        update_payload = {"id": int(session_id_to_use), "name": new_session_name}
        if model_to_use: update_payload["model"] = model_to_use
        if temperature_to_use is not None: update_payload["temperature"] = temperature_to_use
        
        logger.info(f"Attempting to update and rename Session {session_id_to_use} with payload: {json.dumps(update_payload)}")
        update_response = await client.post(SESSION_API_URL, headers=headers, json=update_payload)
        update_response.raise_for_status()
        logger.info(f"✅ Successfully updated and renamed Session {session_id_to_use} to '{new_session_name}'.")
        await asyncio.sleep(0.8)
    except Exception as e:
        if 'session_id_to_use' in locals() and session_id_to_use:
            await session_id_ammo_box.put(session_id_to_use)
        logger.error(f"❌ Failed during session setup. Error: {e}. Session ID returned to queue if available.", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set session parameters on the backend.")

    # --- Step 3: Prepare and Stream the Chat Request (with full context) ---
    messages = openai_request.get("messages", [])
    
    # **** USE THE NEW FUNCTION TO RECONSTRUCT THE FULL PROMPT ****
    full_prompt = reconstruct_prompt_from_messages(messages)
    
    logger.info(f"Reconstructed full prompt for backend:\n---\n{full_prompt}\n---")
    
    xjtlu_payload = {"text": full_prompt, "files": [], "sessionId": session_id_to_use}

    async def stream_generator():
        # (The streaming logic itself does not need to change)
        try:
            logger.info(f"Proxying chat request for Session ID: {session_id_to_use}")
            async with client.stream("POST", CHAT_API_URL, json=xjtlu_payload, headers=headers) as response:
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
        
        except Exception as e:
            logger.error(f"Error during streaming for session {session_id_to_use}: {e}", exc_info=True)
        finally:
            logger.info(f"Request for session {session_id_to_use} is complete. Triggering background task to replenish ammo.")
            asyncio.create_task(replenish_session_id_ammo())
            
    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@app.get("/", include_in_schema=False)
def root():
    return {"message": "XJTLU GenAI Adapter (Full Context Reconstruction) is running.", "status": "ok"}