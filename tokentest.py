# test_token_heartbeat.py - 使用已有的心跳SessionID和saveSession方法来测试token
import os
import httpx
import json
from datetime import datetime
from dotenv import load_dotenv, find_dotenv, set_key
import sys

# ================== 配置 ==================
BASE_URL = "https://jmapi.xjtlu.edu.cn/api/chat"
# 目标接口仍然是 saveSession
SESSION_API_URL = f"{BASE_URL}/saveSession?sf_request_type=ajax"
# ==========================================

def get_headers():
    """获取请求头"""
    jm_token = os.getenv("JM_TOKEN")
    sdp_session = os.getenv("SDP_SESSION")
    
    if not jm_token or not sdp_session:
        print("❌ 错误: 未找到 JM_TOKEN 或 SDP_SESSION 环境变量。")
        sys.exit(1)
    
    return {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://xipuai.xjtlu.edu.cn",
        "referer": "https://xipuai.xjtlu.edu.cn/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "jm-token": jm_token,
        "sdp-app-session": sdp_session,
    }

def test_heartbeat_with_existing_session():
    """使用已有的心跳Session ID和saveSession方法测试token状态"""
    # 加载环境变量
    env_file = find_dotenv()
    if not env_file:
        print("❌ 错误: 未找到 .env 文件。")
        return False
        
    load_dotenv(env_file, override=True)
    
    # 获取心跳session ID
    heartbeat_session_id = os.getenv("HEARTBEAT_SESSION_ID")
    if not heartbeat_session_id:
        print("❌ 错误: 未找到 HEARTBEAT_SESSION_ID 环境变量。")
        print("   请确保已至少运行过一次主程序 (adapter.py) 来创建并保存此ID。")
        return False

    # 准备请求 - 更新已有的心跳会话来验证token
    headers = get_headers()
    # 在payload中包含 'id'，这将触发更新操作而不是创建
    payload = {
        "id": int(heartbeat_session_id), # API需要整型的ID
        "name": f"Persistent Heartbeat Session (Last Check: {datetime.now().strftime('%H:%M:%S')})",
        "model": "qwen-2.5-72b",
        "temperature": 0.7,
        "maxToken": 0,
        "presencePenalty": 0,
        "frequencyPenalty": 0
    }
    
    print(f"\n🔍 Token 过期检测工具 (更新现有心跳会话)")
    print(f"📅 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 目标URL: {SESSION_API_URL}")
    print(f"💓 使用心跳Session ID: {heartbeat_session_id}")
    print("-" * 50)
    
    try:
        with httpx.Client(timeout=30.0) as client:
            print(f"📡 正在发送 saveSession 请求以更新会话 {heartbeat_session_id}...")
            response = client.post(SESSION_API_URL, headers=headers, json=payload)
            
            print(f"📡 HTTP状态码: {response.status_code}")
            
            try:
                data = response.json()
                print("\n📄 XipuAI 服务器返回内容:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print("-" * 50)

                # jmapi的成功标志是 code == 0
                if response.status_code == 200 and data.get("code") == 0:
                    print(f"\n✅ Token有效！(成功更新会话 {heartbeat_session_id})")
                    set_key(env_file, "EXPIRE", "False")
                    print("✅ 已更新环境变量: EXPIRE=False")
                    return True
                else:
                    error_msg = data.get("msg", "无具体错误信息")
                    print(f"\n❌ Token无效或请求失败！(响应码 code: {data.get('code')}, 消息: {error_msg})")
                    set_key(env_file, "EXPIRE", "True")
                    print("❌ 已更新环境变量: EXPIRE=True")
                    return False

            except json.JSONDecodeError:
                print("\n❌ 错误: 无法解析服务器响应为JSON。")
                print("📄 原始响应内容:")
                print(response.text)
                print("-" * 50)
                set_key(env_file, "EXPIRE", "True")
                print("❌ 已更新环境变量: EXPIRE=True")
                return False
                    
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP错误: {e}")
        print(f"响应内容: {e.response.text if hasattr(e, 'response') else '无'}")
        set_key(env_file, "EXPIRE", "True")
        print("❌ 已更新环境变量: EXPIRE=True")
        return False
        
    except Exception as e:
        print(f"\n❌ 发生未知错误: {type(e).__name__}: {e}")
        set_key(env_file, "EXPIRE", "True")
        print("❌ 已更新环境变量: EXPIRE=True")
        return False

def main():
    """主函数"""
    print("🚀 启动Token过期检测...")
    
    is_valid = test_heartbeat_with_existing_session()
    
    print("\n" + "=" * 50)
    if is_valid:
        print("✅ 检测完成: Token有效。")
        sys.exit(0)
    else:
        print("❌ 检测完成: Token已过期或无效。")
        sys.exit(1)

if __name__ == "__main__":
    main()
