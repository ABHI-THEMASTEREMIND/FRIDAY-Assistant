@echo off
echo FRIDAY needs Ollama and one local AI model.
echo.
echo 1. The official Ollama download page will open.
echo 2. Download and run the Ollama installer. Finish the installation.
echo 3. This script will download FRIDAY's AI model.
start "" "https://ollama.com/download/windows"
echo.
echo Return to this window only after the Ollama installer says it is complete.
pause
set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not exist "%OLLAMA_EXE%" set "OLLAMA_EXE=%ProgramFiles%\Ollama\ollama.exe"
if not exist "%OLLAMA_EXE%" (
  echo Ollama was not found yet. Install it first, then run this file again.
  pause
  exit /b 1
)
"%OLLAMA_EXE%" pull qwen3:4b
echo.
echo Setup complete. You can now start FRIDAY.
pause
