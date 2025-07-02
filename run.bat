@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 打印启动横幅
echo ================================================================
echo 🚀 XJTLU GenAI Adapter - 智能启动器
echo ================================================================

:: 步骤1: 环境初始化
echo.
echo ▶️  步骤 1/3: 初始化Conda环境
echo 📝 激活环境: genai_project
echo --------------------------------------------------
call conda activate genai_project
if !errorlevel! neq 0 (
    echo ❌ Conda环境激活失败！
    echo 请检查是否已安装Conda并创建了genai_project环境
    pause
    exit /b 1
)
echo ✅ Conda环境激活成功

:: 步骤2: 运行预检查脚本
echo.
echo ▶️  步骤 2/3: 运行环境预检查
echo 📝 执行命令: python precheck.py
echo --------------------------------------------------
python precheck.py
set BRANCH_CODE=!errorlevel!

echo.
echo 📊 预检查完成，状态码: !BRANCH_CODE!

:: 步骤3: 根据状态码执行相应流程
echo.
echo ▶️  步骤 3/3: 执行启动流程
echo --------------------------------------------------

if !BRANCH_CODE! == 0 (
    echo 🌿 执行 Branch 0 流程: 直接启动服务
    call :start_service
) else if !BRANCH_CODE! == 1 (
    echo 🌿 执行 Branch 1 流程: 配置 → 认证 → 启动
    call :branch1_flow
) else if !BRANCH_CODE! == 2 (
    echo 🌿 执行 Branch 2 流程: 认证 → 启动
    call :branch2_flow
) else if !BRANCH_CODE! == 3 (
    echo 🌿 执行 Branch 3 流程: 重新认证 → 启动
    call :branch3_flow
) else if !BRANCH_CODE! == 99 (
    echo ❌ 预检查过程出现错误，程序退出
    goto :error_exit
) else (
    echo ❌ 未知的状态码: !BRANCH_CODE!
    goto :error_exit
)

goto :end

:: ====================================================================
:: 函数定义区域
:: ====================================================================

:run_command
:: 参数: %1=命令, %2=描述
echo.
echo ▶️  %~2
echo 📝 执行命令: %~1
echo --------------------------------------------------
%~1
if !errorlevel! neq 0 (
    echo ❌ %~2 - 执行失败 ^(错误代码: !errorlevel!^)
    exit /b 1
) else (
    echo ✅ %~2 - 成功完成
    exit /b 0
)

:branch1_flow
:: Branch 1: 配置 → 认证 → 启动
echo 流程: 配置凭据 → 获取令牌 → 启动服务

call :run_command "python config.py" "步骤 1/3: 配置用户凭据"
if !errorlevel! neq 0 (
    echo.
    echo ❌ 配置失败，请检查输入并重试
    goto :error_exit
)

timeout /t 2 /nobreak >nul

call :run_command "python auth.py" "步骤 2/3: 获取认证令牌"
if !errorlevel! neq 0 (
    echo.
    echo ❌ 认证失败，请检查凭据是否正确
    goto :error_exit
)

timeout /t 2 /nobreak >nul

echo.
echo ✨ 所有准备工作完成，正在启动服务...
call :start_service
exit /b

:branch2_flow
:: Branch 2: 认证 → 启动
echo 流程: 获取令牌 → 启动服务

call :run_command "python auth.py" "步骤 1/2: 获取认证令牌"
if !errorlevel! neq 0 (
    echo.
    echo ❌ 认证失败，请检查凭据是否正确
    goto :error_exit
)

timeout /t 2 /nobreak >nul

echo.
echo ✨ 令牌获取成功，正在启动服务...
call :start_service
exit /b

:branch3_flow
:: Branch 3: 重新认证 → 启动
echo 流程: 重新获取令牌 → 启动服务

call :run_command "python auth.py" "步骤 1/2: 重新获取认证令牌"
if !errorlevel! neq 0 (
    echo.
    echo ❌ 重新认证失败，请检查凭据是否正确
    goto :error_exit
)

timeout /t 2 /nobreak >nul

echo.
echo ✨ 令牌刷新成功，正在启动服务...
call :start_service
exit /b

:start_service
:: 启动API服务
echo.
echo ▶️  启动API适配器服务
echo 📝 执行命令: uvicorn adapter:app --reload
echo --------------------------------------------------
echo.
echo ================================================================
echo 🎉 服务启动成功！
echo 📡 API服务正在运行: http://localhost:8000
echo 📖 API文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo ================================================================
echo.

uvicorn adapter:app --reload
if !errorlevel! neq 0 (
    echo ❌ 服务启动失败
    goto :error_exit
)
exit /b

:error_exit
echo.
echo ================================================================
echo ❌ 服务启动失败
echo 请检查上面的错误信息并重试
echo ================================================================
pause
exit /b 1

:end
echo.
echo ================================================================
echo ⛔ 服务已停止
echo ================================================================
pause
exit /b 0