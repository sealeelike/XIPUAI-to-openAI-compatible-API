# precheck.py - 预检查脚本，根据环境变量状态执行不同分支
import os
import subprocess
import sys
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

def print_banner():
    """打印启动横幅"""
    print("=" * 60)
    print("🚀 XJTLU GenAI 服务启动器")
    print("=" * 60)

def check_env_file():
    """检查.env文件是否存在"""
    env_file = find_dotenv()
    if not env_file or not os.path.exists(".env"):
        return False
    return True

def load_env_variables():
    """加载环境变量"""
    env_file = find_dotenv()
    if env_file:
        load_dotenv(env_file, override=True)

def check_credentials():
    """检查用户名和密码是否存在"""
    username = os.getenv("XJTLU_USERNAME")
    password = os.getenv("XJTLU_PASSWORD")
    
    if not username or not password or username.strip() == "" or password.strip() == "":
        return False
    return True

def check_tokens():
    """检查token相关环境变量是否存在"""
    jm_token = os.getenv("JM_TOKEN")
    sdp_session = os.getenv("SDP_SESSION") 
    heartbeat_session_id = os.getenv("HEARTBEAT_SESSION_ID")
    
    tokens_exist = {
        "jm_token": bool(jm_token and jm_token.strip()),
        "sdp_session": bool(sdp_session and sdp_session.strip()),
        "heartbeat_session_id": bool(heartbeat_session_id and heartbeat_session_id.strip())
    }
    
    return tokens_exist

def run_script(script_name, description):
    """运行指定脚本"""
    print(f"\n🔄 {description}...")
    print(f"📝 执行: python {script_name}")
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, 
                              text=True, 
                              check=True)
        print(f"✅ {script_name} 执行成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} 执行失败")
        print(f"❌ 退出码: {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ 执行 {script_name} 时发生错误: {e}")
        return False

def start_service():
    """启动服务"""
    print(f"\n🚀 启动服务...")
    print(f"📝 执行: uvicorn adapter:app --reload")
    
    try:
        # 使用subprocess.run启动服务，不捕获输出让其直接显示
        subprocess.run(["uvicorn", "adapter:app", "--reload"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务启动失败，退出码: {e.returncode}")
        return False
    except FileNotFoundError:
        print("❌ 未找到 uvicorn 命令，请确保已安装 fastapi 和 uvicorn")
        print("💡 安装命令: pip install fastapi uvicorn")
        return False
    except KeyboardInterrupt:
        print("\n🛑 用户中断服务")
        return True
    except Exception as e:
        print(f"❌ 启动服务时发生错误: {e}")
        return False

def main():
    """主函数"""
    print_banner()
    
    # 检查.env文件和凭据
    print("🔍 Step 1: 检查环境配置...")
    
    if not check_env_file():
        print("📄 .env 文件不存在")
        print("🎯 分支选择: Branch 1 - 初始化配置")
        print("-" * 40)
        
        # Branch 1: 配置 -> 认证 -> 启动服务
        if not run_script("config.py", "配置用户凭据"):
            print("❌ 配置失败，程序退出")
            sys.exit(1)
            
        if not run_script("auth.py", "获取认证令牌"):
            print("❌ 认证失败，程序退出")
            sys.exit(1)
            
        start_service()
        return
    
    # 加载环境变量
    load_env_variables()
    
    if not check_credentials():
        print("👤 用户凭据缺失或为空")
        print("🎯 分支选择: Branch 1 - 重新配置")
        print("-" * 40)
        
        # Branch 1: 配置 -> 认证 -> 启动服务
        if not run_script("config.py", "重新配置用户凭据"):
            print("❌ 配置失败，程序退出")
            sys.exit(1)
            
        if not run_script("auth.py", "获取认证令牌"):
            print("❌ 认证失败，程序退出")
            sys.exit(1)
            
        start_service()
        return
    
    print("✅ 用户凭据存在")
    
    # 检查token状态
    print("🔍 Step 2: 检查认证令牌...")
    tokens_status = check_tokens()
    
    missing_tokens = [key for key, exists in tokens_status.items() if not exists]
    
    if missing_tokens:
        print(f"🔑 缺失令牌: {', '.join(missing_tokens)}")
        print("🎯 分支选择: Branch 2 - 重新认证")
        print("-" * 40)
        
        # Branch 2: 认证 -> 启动服务
        if not run_script("auth.py", "获取认证令牌"):
            print("❌ 认证失败，程序退出")
            sys.exit(1)
            
        start_service()
        return
    
    print("✅ 所有认证令牌存在")
    
    # 检查token是否过期
    print("🔍 Step 3: 检查令牌有效性...")
    print("🎯 分支选择: Branch 3 - 令牌有效性检查")
    print("-" * 40)
    
    # Branch 3: 测试token
    if not run_script("tokentest.py", "检查令牌有效性"):
        print("❌ 令牌检查失败，尝试重新认证")
        if not run_script("auth.py", "重新获取认证令牌"):
            print("❌ 认证失败，程序退出")
            sys.exit(1)
        start_service()
        return
    
    # 重新加载环境变量以获取EXPIRE状态
    load_env_variables()
    expire_status = os.getenv("EXPIRE", "").lower()
    
    if expire_status == "false":
        print("✅ 令牌有效")
        print("🎯 分支选择: Branch 3-1 - 直接启动服务")
        print("-" * 40)
        start_service()
    elif expire_status == "true":
        print("⚠️  令牌已过期")
        print("🎯 分支选择: Branch 3-2 - 重新认证后启动")
        print("-" * 40)
        
        if not run_script("auth.py", "重新获取认证令牌"):
            print("❌ 认证失败，程序退出")
            sys.exit(1)
            
        start_service()
    else:
        print(f"⚠️  无法确定令牌状态 (EXPIRE={expire_status})，尝试重新认证")
        if not run_script("auth.py", "重新获取认证令牌"):
            print("❌ 认证失败，程序退出")
            sys.exit(1)
            
        start_service()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 用户中断程序")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序执行过程中发生未知错误: {e}")
        sys.exit(1)