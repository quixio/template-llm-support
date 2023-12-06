import os
from quixstreams import Application, State, message_key
from quixstreams.models.serializers.quix import QuixDeserializer, QuixTimeseriesSerializer
from llm_bot import LlmBot
from draft_producer import DraftProducer
import time

role = os.environ["role"]


app = Application.Quix("transformation-v10-"+role, auto_offset_reset="latest")

input_topic = app.topic(os.environ["output"], value_deserializer=QuixDeserializer())
output_topic = app.topic(os.environ["output"], value_serializer=QuixTimeseriesSerializer())
draft_producer = DraftProducer(os.environ["draft_topic"])
state_key = "conversation-history-v2"
director_prompt_state_key = "director_prompt_state_key-v1"

product = os.environ["product"]
scenario = os.environ["scenario"].format(product)

llm_bot = LlmBot(product, scenario, draft_producer)




llm = Llama(model_path="./state/llama-2-7b-chat.Q4_K_M.gguf")
    
def generate_response(message):
    
    result = llm(
        prompt=get_promt(message),
        max_tokens=250,
        temperature=0.7,
        top_p=0.95,
        stop=["AGENT:","CUSTOMER:","\n"],
        repeat_penalty=1.2,
        top_k=150,
        echo=True
    )

    finalreply = result["choices"][0]["text"]
    finalreply = finalreply.replace(prompt, ' ').replace('{', '').replace('}', '').replace('"', '').strip()

    return finalreply


sdf = app.dataframe(input_topic)

sdf = sdf[sdf["role"] == "customer"]
sdf["role"] = "agent"
sdf["Timestamp"] = sdf["Timestamp"].apply(lambda row: time.time_ns())

sdf["chat-message"] = sdf["chat-message"].apply(generate_response)


sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)



