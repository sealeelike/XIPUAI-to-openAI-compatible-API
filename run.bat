@echo off
setlocal enabledelayedexpansion

:: Change directory to the location of this batch file
cd /d "%~dp0"

:: Activate the conda environment
echo Activating conda environment: genai_project
call conda activate genai_project

:: --- Pre-check for username and password ---
set "needs_config=false"

if not exist .env (
    echo Trigger: .env file not found.
    set "needs_config=true"
) else (
    set "username_found=false"
    set "password_found=false"
    for /f "usebackq delims=" %%a in (".env") do (
        set "line=%%a"
        if /i "!line:~0,15!"=="XJTLU_USERNAME=" (
            set "username_found=true"
            set "username_value=!line:~15!"
            if "!username_value!"=="" (
                echo Trigger: XJTLU_USERNAME is empty.
                set "needs_config=true"
            )
        )
        if /i "!line:~0,15!"=="XJTLU_PASSWORD=" (
            set "password_found=true"
            set "password_value=!line:~15!"
            if "!password_value!"=="" (
                echo Trigger: XJTLU_PASSWORD is empty.
                set "needs_config=true"
            )
        )
    )
    if !username_found! == false (
        echo Trigger: XJTLU_USERNAME not found in .env.
        set "needs_config=true"
    )
    if !password_found! == false (
        echo Trigger: XJTLU_PASSWORD not found in .env.
        set "needs_config=true"
    )
)

if !needs_config! == true (
    echo Running config.py...
    python config.py
)

:: --- Pre-check for HEARTBEAT_SESSION_ID ---
set "run_auth_directly=false"
set "session_id_found=false"
if exist .env (
    for /f "usebackq delims=" %%a in (".env") do (
        set "line=%%a"
        if /i "!line:~0,23!"=="HEARTBEAT_SESSION_ID=" (
            set "session_id_found=true"
            set "session_id_value=!line:~23!"
            if "!session_id_value!"=="" (
                echo Trigger: HEARTBEAT_SESSION_ID is empty.
                set "run_auth_directly=true"
            )
        )
    )
    if !session_id_found! == false (
        echo Trigger: HEARTBEAT_SESSION_ID not found in .env.
        set "run_auth_directly=true"
    )
)

if !run_auth_directly! == true (
    echo Running auth.py to get a new session...
    python auth.py
    echo Starting server...
    uvicorn adapter:app --reload
    goto :end
)

:: Run the token test script
echo Running token test...
python tokentest.py

:: Read the EXPIRE variable from the .env file
set "EXPIRE_VALUE="
if exist .env (
    for /f "usebackq delims=" %%a in (".env") do (
        set "line=%%a"
        if /i "!line:~0,7!"=="EXPIRE=" (
            set "EXPIRE_VALUE=!line:~7!"
            set "EXPIRE_VALUE=!EXPIRE_VALUE:'=!"
        )
    )
)

echo Found EXPIRE=%EXPIRE_VALUE%

:: Conditional execution based on the value of EXPIRE
if /i "%EXPIRE_VALUE%"=="True" (
    echo EXPIRE is True. Running auth.py before starting the server.
    python auth.py
    uvicorn adapter:app --reload
) else if /i "%EXPIRE_VALUE%"=="False" (
    echo EXPIRE is False. Starting the server directly.
    uvicorn adapter:app --reload
) else (
    echo EXPIRE variable not set, or value is not True/False in .env file. Server not started.
)

:end
pause
endlocal
