# LLM Powered Customer Success Dashboard with Sentiment Analysis

This template uses Quix and Llama 2 to create a Customer Success Dashboard with Sentiment Analysis.

## Pipeline

This project consists of five applications:

    1. AI Customer: an LLM-powered chatbot simulating a customer requesting support regarding a defect of an appliance they bought from an electronics company.
    2. AI Customer Support Agent: an LLM-powered customer support agent trying to assist the AI Customer with a support request.
    3. Sentiment Analyzer: an application performing sentiment analysis on the conversation between the customer and the customer support agent.
    4. Redis Sink: an application that saves conversation history and the results of sentiment analysis to Redis.
    5. Streamlit Dashboard: a customer success dashboard displaying active conversations between customers and support agents and the results of sentiment analysis to gain insights into customer satisfaction and improve customer success and support efforts.