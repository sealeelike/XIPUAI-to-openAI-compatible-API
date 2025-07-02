# test_token_heartbeat.py - 测试token是否过期的轻量脚本
import os
import httpx
import json
from datetime import datetime
from dotenv import load_dotenv, find_dotenv, set_key
import sys

# 配置
BASE_URL = "https://jmapi.xjtlu.edu.cn/api/chat"
CHAT_API_URL = f"{BASE_URL}/completions?sf_request_type=fetch"

def get_headers():
    """获取请求头"""
    jm_token = os.getenv("JM_TOKEN")
    sdp_session = os.getenv("SDP_SESSION")
    
    if not jm_token or not sdp_session:
        print("❌ 错误: 未找到 JM_TOKEN 或 SDP_SESSION 环境变量")
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

def test_heartbeat():
    """测试心跳并检查token状态"""
    # 加载环境变量
    env_file = find_dotenv()
    load_dotenv(env_file, override=True)
    
    # 获取心跳session ID
    heartbeat_session_id = os.getenv("HEARTBEAT_SESSION_ID")
    if not heartbeat_session_id:
        print("❌ 错误: 未找到 HEARTBEAT_SESSION_ID 环境变量")
        print("请先运行主程序创建心跳会话")
        sys.exit(1)
    
    # 准备请求 - 发送一个空的聊天请求作为心跳
    headers = get_headers()
    payload = {
        "text": "ping",  # 简单的心跳消息
        "files": [],
        "sessionId": heartbeat_session_id
    }
    
    print(f"\n🔍 Token 过期检测工具")
    print(f"📅 检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 目标URL: {CHAT_API_URL}")
    print(f"💓 使用心跳Session ID: {heartbeat_session_id}")
    print("-" * 50)
    
    try:
        # 发送请求
        with httpx.Client(timeout=30.0) as client:
            # 使用stream方式发送请求，但立即关闭
            with client.stream("POST", CHAT_API_URL, headers=headers, json=payload) as response:
                # 获取状态码
                status_code = response.status_code
                print(f"📡 HTTP状态码: {status_code}")
                
                # 读取第一行响应来判断是否成功
                first_line = None
                try:
                    for line in response.iter_lines():
                        first_line = line
                        break
                except Exception:
                    pass
                
                # 判断token是否过期
                if status_code == 200:
                    print(f"📄 首行响应: {first_line}")
                    print("\n✅ Token有效！")
                    set_key(env_file, "EXPIRE", "False")
                    print("✅ 已设置环境变量: EXPIRE=False")
                    return True
                else:
                    # 尝试读取错误信息
                    error_content = ""
                    try:
                        for line in response.iter_lines():
                            error_content += line + "\n"
                            if len(error_content) > 500:  # 限制错误信息长度
                                break
                    except Exception:
                        pass
                    
                    print(f"📄 错误响应: {error_content[:500]}")
                    print("\n❌ Token可能已过期或请求失败！")
                    set_key(env_file, "EXPIRE", "True")
                    print("❌ 已设置环境变量: EXPIRE=True")
                    return False
                    
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP错误: {e}")
        print(f"响应内容: {e.response.text if hasattr(e, 'response') else '无'}")
        set_key(env_file, "EXPIRE", "True")
        print("❌ 已设置环境变量: EXPIRE=True")
        return False
        
    except Exception as e:
        print(f"\n❌ 发生错误: {type(e).__name__}: {e}")
        set_key(env_file, "EXPIRE", "True")
        print("❌ 已设置环境变量: EXPIRE=True")
        return False

def main():
    """主函数"""
    print("🚀 启动Token过期检测...")
    
    # 检查必要的环境变量
    env_file = find_dotenv()
    if not env_file:
        print("❌ 错误: 未找到 .env 文件")
        sys.exit(1)
    
    load_dotenv(env_file)
    
    # 执行测试
    is_valid = test_heartbeat()
    
    print("\n" + "=" * 50)
    if is_valid:
        print("✅ 检测完成: Token有效")
        sys.exit(0)
    else:
        print("❌ 检测完成: Token已过期或无效")
        sys.exit(1)

if __name__ == "__main__":
    main()
