# precheck.py - 环境状态检查和分支决策脚本
import os
import sys
import subprocess
from dotenv import load_dotenv, find_dotenv

def print_banner():
    """打印检查横幅"""
    print("=" * 60)
    print("🔍 XJTLU GenAI Adapter - 环境预检查")
    print("=" * 60)

def check_env_status():
    """检查环境变量状态并返回分支类型"""
    print("\n🔍 检查环境配置状态...")
    
    # 查找.env文件
    env_file = find_dotenv()
    if not env_file:
        print("📄 .env文件: ❌ 不存在")
        print("\n🔀 检测结果: Branch 1 - 需要配置用户凭据")
        return 1
    
    print(f"📄 .env文件: ✅ 找到 ({env_file})")
    
    # 加载环境变量
    load_dotenv(env_file, override=True)
    
    # 检查各项环境变量
    env_status = {
        "username": os.getenv("XJTLU_USERNAME"),
        "password": os.getenv("XJTLU_PASSWORD"),
        "jm_token": os.getenv("JM_TOKEN"),
        "sdp_session": os.getenv("SDP_SESSION"),
        "heartbeat_id": os.getenv("HEARTBEAT_SESSION_ID"),
        "expire": os.getenv("EXPIRE", "").lower()
    }
    
    # 打印环境变量状态
    print("\n📊 环境变量检查结果:")
    print(f"  • XJTLU_USERNAME: {'✅ 存在' if env_status['username'] else '❌ 缺失'}")
    print(f"  • XJTLU_PASSWORD: {'✅ 存在' if env_status['password'] else '❌ 缺失'}")
    print(f"  • JM_TOKEN: {'✅ 存在' if env_status['jm_token'] else '❌ 缺失'}")
    print(f"  • SDP_SESSION: {'✅ 存在' if env_status['sdp_session'] else '❌ 缺失'}")
    print(f"  • HEARTBEAT_SESSION_ID: {'✅ 存在' if env_status['heartbeat_id'] else '❌ 缺失'}")
    if env_status['expire']:
        print(f"  • EXPIRE: {env_status['expire']}")
    
    # 判断分支
    if not env_status['username'] or not env_status['password']:
        print("\n🔀 检测结果: Branch 1 - 需要配置用户凭据")
        return 1
    
    if not all([env_status['jm_token'], env_status['sdp_session'], env_status['heartbeat_id']]):
        print("\n🔀 检测结果: Branch 2 - 需要获取认证令牌")
        return 2
    
    print("\n🔀 检测结果: Branch 3 - 需要检查令牌有效性")
    return 3

def check_token_validity():
    """检查令牌有效性"""
    print("\n🔍 检查令牌有效性...")
    print("-" * 50)
    
    try:
        # 运行tokentest.py
        result = subprocess.run([sys.executable, "tokentest.py"], 
                              capture_output=True, text=True, check=False)
        
        # tokentest.py总是返回0，所以我们需要检查EXPIRE环境变量
        load_dotenv(override=True)
        expire_status = os.getenv("EXPIRE", "").lower()
        
        if expire_status == "false":
            print("✅ 令牌检查完成 - 令牌有效")
            return 0  # 直接启动服务
        else:
            print("⚠️  令牌检查完成 - 令牌已过期")
            return 3  # 需要重新认证
            
    except Exception as e:
        print(f"❌ 令牌检查过程出现错误: {e}")
        print("将假定令牌无效，需要重新认证")
        return 3

def main():
    """主函数"""
    print_banner()
    
    try:
        # 检查环境状态
        branch_code = check_env_status()
        
        # 如果是Branch 3，需要进一步检查令牌
        if branch_code == 3:
            branch_code = check_token_validity()
        
        # 打印最终决策
        print("\n" + "=" * 60)
        branch_names = {
            0: "Branch 0 - 直接启动服务（令牌有效）",
            1: "Branch 1 - 配置凭据 → 获取令牌 → 启动服务", 
            2: "Branch 2 - 获取令牌 → 启动服务",
            3: "Branch 3 - 重新认证 → 启动服务"
        }
        
        print(f"🚀 最终决策: {branch_names.get(branch_code, '未知分支')}")
        print(f"📤 返回状态码: {branch_code}")
        print("=" * 60)
        
        # 返回状态码给bat脚本
        sys.exit(branch_code)
        
    except KeyboardInterrupt:
        print("\n\n⛔ 用户中断执行")
        sys.exit(99)
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {e}")
        sys.exit(99)

if __name__ == "__main__":
    main()