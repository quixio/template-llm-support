#!/bin/bash
set -e

# Download the model file
echo "Downloading model..."
wget -P /models/ https://huggingface.co/TheBloke/Llama-2-7b-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf

# Start the main application
echo "Starting application..."
exec "/bin/sh" "/app/docker/simple/run.sh"
