@echo off
REM ===== 切换到脚本所在目录 =====
cd /d "%~dp0"

REM ===== 激活 conda 环境 =====
call conda activate genai_project

REM ===== 运行验证脚本 =====
python auth.py

REM ===== 启动 uvicorn 服务 =====
uvicorn adapter:app --reload

REM （可选）脚本执行完毕后暂停，方便查看日志
pause
