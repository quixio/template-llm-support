@echo off
SET FILE_PATH=llama-2-7b-chat.Q4_K_M.gguf

powershell -Command "If (!(Test-Path %FILE_PATH%)) { Invoke-WebRequest -Uri 'https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf?download=true' -OutFile %FILE_PATH% }"

docker-compose up -d --build --remove-orphans