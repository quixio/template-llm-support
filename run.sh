#!/bin/bash

FILE_PATH="llama-2-7b-chat.Q4_K_M.gguf"

# Check if the file exists
if [ ! -f "$FILE_PATH" ]; then
    # If the file doesn't exist, download it
    wget -O $FILE_PATH https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf?download=true
fi

# Run Docker Compose
docker-compose up -d --build --remove-orphans