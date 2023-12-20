# LLM-powered customer success dashboard

This template uses Quix and Llama 2 to create a Customer Success Dashboard with Sentiment Analysis.

## Technologies used

Some of the technologies used by this template project are listed here.

**Infrastructure:**

- [Quix](https://quix.io/)
- [Docker](https://www.docker.com/)
- [Kubernetes](https://kubernetes.io/)
- [Redis](https://redis.com/)

**Backend:**

- [Quix Streams](https://github.com/quixio/quix-streams)
- [pandas](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html)
- [llama.cpp](https://github.com/ggerganov/llama.cpp)
- [LangChain](https://python.langchain.com/)

**Frontend:**

- [Streamlit](https://streamlit.io/)
- [Microsoft SignalR](https://learn.microsoft.com/en-us/aspnet/signalr/)

## The project pipeline

This project consists of following applications:

1. _AI Customer_: an LLM-powered chatbot simulating a customer requesting support regarding a defect of an appliance they bought from an electronics company.
2. _AI Customer Support Agent_: an LLM-powered customer support agent trying to assist the AI Customer with a support request.
3. _Sentiment Analyzer_: an application performing sentiment analysis on the conversation between the customer and the customer support agent.
4. _Redis Sink_: an application that saves conversation history and the results of sentiment analysis to Redis.
5. _Streamlit Dashboard_: a customer success dashboard displaying active conversations between customers and support agents and the results of sentiment analysis to gain insights into customer satisfaction and improve customer success and support efforts.

## Prerequisites

To get started make sure you have a [free Quix account](https://portal.platform.quix.io/self-sign-up).

If you are new to Quix it is worth reviewing the [recent changes page](https://quix.io/docs/platform/changes.html), as that contains very useful information about the significant recent changes, and also has a number of useful videos you can watch to gain familiarity with Quix.

### Git provider

You also need to have a Git account. This could be GitHub, Bitbucket, GitLab, or any other Git provider you are familar with, and that supports SSH keys. The simplest option is to create a free [GitHub account](https://github.com).

While this project uses an external Git account, Quix can also provide a Quix-hosted Git solution using Gitea for your own projects. You can watch a video on [how to create a project using Quix-hosted Git](https://www.loom.com/share/b4488be244834333aec56e1a35faf4db?sid=a9aa124a-a2b0-45f1-a756-11b4395d0efc).

## Tutorial

Check out our [tutorials](https://quix.io/docs/platform/tutorials/).
A specific tutorial for this template is coming soon.