from draft_producer import DraftProducer


class LlmBot:
    

    def __init__(self, product: str, scenario: str, draft_producer: DraftProducer):
        
        file_path = Path('./state/llama-2-7b-chat.Q4_K_M.gguf')
        REPO_ID = "TheBloke/Llama-2-7b-Chat-GGUF"
        FILENAME = "llama-2-7b-chat.Q4_K_M.gguf"
        state_key = "conversation-history-v1"

        if not file_path.exists():
            # perform action if the file does not exist
            print('The model path does not exist in state. Downloading model...')
            hf_hub_download(repo_id=REPO_ID, filename=FILENAME, local_dir="state")
        else:
            print('The model has been detected in state. Loading model from state...')

        self.llm = Llama(model_path="./state/llama-2-7b-chat.Q4_K_M.gguf")
        self.draft_producer = draft_producer

    
    def generate_response(self, row, prompt, max_tokens=250, temperature=0.7, top_p=0.95, repeat_penalty=1.2, top_k=150):
        draft_producer.produce(row, message_key())
        
        result = self.llm(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=True,
            stop=["AGENT:","CUSTOMER:","\n"],
            repeat_penalty=repeat_penalty,
            top_k=top_k,
            echo=True
        )


        response = ""
        for iteration in result:
            iteration_text = iteration["choices"][0]["text"]
            response += iteration_text
            row["chat-message"] = response
            self.draft_producer.produce(row, bytes.decode(message_key()))
            print(str(iteration_text), end="", flush=True)

        return response
    

