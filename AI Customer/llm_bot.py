

class LLM_bot:


    def __init__(self, topic: str):
        

    
    def generate_response(self, row, prompt, max_tokens=250, temperature=0.7, top_p=0.95, repeat_penalty=1.2, top_k=150):
    
        draft_producer.produce(row, message_key())
        
        result = llm(
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
            draft_producer.produce(row, bytes.decode(message_key()))
            print(str(iteration_text), end="", flush=True)

        return response
    

