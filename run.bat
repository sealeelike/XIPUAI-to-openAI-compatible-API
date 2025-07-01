@echo off
REM ===== 切换到脚本所在目录 =====
cd /d "%~dp0"

REM ===== 检查 .env 文件和用户名/密码环境变量 =====
set "runConfig=false"

REM 如果 .env 文件不存在
if not exist ".env" (
    echo [INFO] .env not found.
    set "runConfig=true"
)

REM 如果 XJTLU_USERNAME 为空
if "%XJTLU_USERNAME%"=="" (
    echo [INFO] XJTLU_USERNAME is not set.
    set "runConfig=true"
)

REM 如果 XJTLU_PASSWORD 为空
if "%XJTLU_PASSWORD%"=="" (
    echo [INFO] XJTLU_PASSWORD is not set.
    set "runConfig=true"
)

REM 如有任一条件满足，先运行 config.py
if "%runConfig%"=="true" (
    echo [INFO] Running config.py to generate/update .env ...
    python config.py
    if errorlevel 1 (
        echo [ERROR] config.py failed. Exiting.
        exit /b 1
    )
    echo [INFO] config.py completed.
)

REM ===== 激活 conda 环境 =====
call conda activate genai_project
if errorlevel 1 (
    echo [ERROR] Failed to activate conda environment 'genai_project'.
    exit /b 1
)

REM ===== 运行验证脚本 =====
echo [INFO] Running authopus.py ...
python authopus.py
if errorlevel 1 (
    echo [ERROR] authopus.py failed. Exiting.
    exit /b 1
)

REM ===== 启动 uvicorn 服务 =====
echo [INFO] Starting uvicorn server ...
uvicorn adapter:app --reload
if errorlevel 1 (
    echo [ERROR] uvicorn failed to start.
    exit /b 1
)

REM （可选）脚本执行完毕后暂停，方便查看日志
pause
