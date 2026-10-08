@echo off
rem Write the TinyFish API key into this project's .env (read by tinyfish_search).
rem
rem Usage:
rem   set-tinyfish-key.bat sk-tinyfish-xxxx     :: pass the key directly
rem   set-tinyfish-key.bat                      :: prompt for it
rem
rem Get a free key at https://tinyfish.ai  (Search API free tier: 12000/day).
rem
rem NOTE: keep this file ASCII-only. cmd.exe parses .bat with the console code
rem       page (GBK on Chinese Windows), so UTF-8 Chinese text in here breaks
rem       the parser ("'ish.ai' is not recognized as an internal or external
rem       command"). Put wording in README.md instead.
setlocal
cd /d "%~dp0"

set "KEY=%~1"
if "%KEY%"=="" set /p "KEY=TinyFish API key (https://tinyfish.ai): "
if "%KEY%"=="" (
    echo No key given, nothing changed.
    exit /b 1
)

set "TMPF=%TEMP%\mon3tr-env-%RANDOM%%RANDOM%.tmp"
if exist ".env" (
    findstr /v /b /i "TINYFISH_API_KEY" ".env" > "%TMPF%"
    if errorlevel 2 (
        echo Failed to read the existing .env, nothing changed.
        exit /b 1
    )
) else (
    type nul > "%TMPF%"
)
>> "%TMPF%" echo TINYFISH_API_KEY=%KEY%
move /y "%TMPF%" ".env" >nul

echo Wrote %CD%\.env
echo Restart Mon3tr-MCP to apply, e.g. (Task Scheduler):
echo   schtasks /end /tn Mon3tr-MCP ^&^& schtasks /run /tn Mon3tr-MCP
endlocal
