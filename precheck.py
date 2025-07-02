# precheck.py - 智能预检查和启动脚本
import os
import sys
import subprocess
from dotenv import load_dotenv, find_dotenv
import time

def print_banner():
    """打印启动横幅"""
    print("=" * 60)
    print("🚀 XJTLU GenAI Adapter - 智能启动器")
    print("=" * 60)

def run_command(command, description):
    """运行命令并显示状态"""
    print(f"\n▶️  {description}")
    print(f"📝 执行命令: {command}")
    print("-" * 50)
    
    try:
        # 使用shell=True以支持更复杂的命令
        result = subprocess.run(command, shell=True, check=True, text=True)
        print(f"✅ {description} - 成功完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - 执行失败")
        print(f"错误代码: {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ {description} - 发生错误: {e}")
        return False

def check_env_status():
    """检查环境变量状态并返回分支类型"""
    print("\n🔍 检查环境配置状态...")
    
    # 查找.env文件
    env_file = find_dotenv()
    if not env_file:
        print("📄 .env文件: ❌ 不存在")
        return "branch1", {}
    
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
        return "branch1", env_status
    
    if not all([env_status['jm_token'], env_status['sdp_session'], env_status['heartbeat_id']]):
        print("\n🔀 检测结果: Branch 2 - 需要获取认证令牌")
        return "branch2", env_status
    
    print("\n🔀 检测结果: Branch 3 - 需要检查令牌有效性")
    return "branch3", env_status

def execute_branch1():
    """执行分支1: 配置 → 认证 → 启动"""
    print("\n🌿 执行 Branch 1 流程")
    print("流程: 配置凭据 → 获取令牌 → 启动服务")
    
    # 步骤1: 运行配置脚本
    if not run_command("python config.py", "步骤 1/3: 配置用户凭据"):
        print("\n❌ 配置失败，请检查输入并重试")
        return False
    
    time.sleep(2)  # 短暂等待
    
    # 步骤2: 运行认证脚本
    if not run_command("python auth.py", "步骤 2/3: 获取认证令牌"):
        print("\n❌ 认证失败，请检查凭据是否正确")
        return False
    
    time.sleep(2)
    
    # 步骤3: 启动服务
    print("\n✨ 所有准备工作完成，正在启动服务...")
    return run_command("uvicorn adapter:app --reload", "步骤 3/3: 启动API适配器服务")

def execute_branch2():
    """执行分支2: 认证 → 启动"""
    print("\n🌿 执行 Branch 2 流程")
    print("流程: 获取令牌 → 启动服务")
    
    # 步骤1: 运行认证脚本
    if not run_command("python auth.py", "步骤 1/2: 获取认证令牌"):
        print("\n❌ 认证失败，请检查凭据是否正确")
        return False
    
    time.sleep(2)
    
    # 步骤2: 启动服务
    print("\n✨ 令牌获取成功，正在启动服务...")
    return run_command("uvicorn adapter:app --reload", "步骤 2/2: 启动API适配器服务")

def execute_branch3(env_status):
    """执行分支3: 检查令牌 → 根据结果决定下一步"""
    print("\n🌿 执行 Branch 3 流程")
    print("流程: 检查令牌有效性 → 决定是否需要重新认证")
    
    # 运行令牌测试
    if not run_command("python tokentest.py", "检查令牌有效性"):
        print("\n⚠️  令牌检查过程出现错误，将尝试重新认证")
        return execute_branch3_2()
    
    # 重新加载环境变量以获取EXPIRE状态
    load_dotenv(override=True)
    expire_status = os.getenv("EXPIRE", "").lower()
    
    if expire_status == "false":
        print("\n✅ 令牌有效！")
        return execute_branch3_1()
    else:
        print("\n⚠️  令牌已过期或无效")
        return execute_branch3_2()

def execute_branch3_1():
    """执行分支3-1: 直接启动服务"""
    print("\n🌿 执行 Branch 3-1 流程")
    print("流程: 直接启动服务（令牌有效）")
    
    print("\n✨ 令牌验证通过，正在启动服务...")
    return run_command("uvicorn adapter:app --reload", "启动API适配器服务")

def execute_branch3_2():
    """执行分支3-2: 重新认证 → 启动"""
    print("\n🌿 执行 Branch 3-2 流程")
    print("流程: 重新获取令牌 → 启动服务")
    
    # 步骤1: 重新运行认证脚本
    if not run_command("python auth.py", "步骤 1/2: 重新获取认证令牌"):
        print("\n❌ 重新认证失败，请检查凭据是否正确")
        return False
    
    time.sleep(2)
    
    # 步骤2: 启动服务
    print("\n✨ 令牌刷新成功，正在启动服务...")
    return run_command("uvicorn adapter:app --reload", "步骤 2/2: 启动API适配器服务")

def main():
    """主函数"""
    print_banner()
    
    try:
        # 检查环境状态
        branch, env_status = check_env_status()
        
        # 根据分支执行相应流程
        success = False
        if branch == "branch1":
            success = execute_branch1()
        elif branch == "branch2":
            success = execute_branch2()
        elif branch == "branch3":
            success = execute_branch3(env_status)
        
        # 最终状态
        print("\n" + "=" * 60)
        if success:
            print("🎉 服务启动成功！")
            print("📡 API服务正在运行: http://localhost:8000")
            print("📖 API文档: http://localhost:8000/docs")
            print("\n按 Ctrl+C 停止服务")
        else:
            print("❌ 服务启动失败")
            print("请检查上面的错误信息并重试")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⛔ 用户中断执行")
        print("服务已停止")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
