from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from strands_tools import http_request
import os

app = BedrockAgentCoreApp()

agent = Agent(
    # model="anthropic.claude-3-5-sonnet-20240620-v1:0",
    system_prompt="You are a helpful AI assistant. you can use API's that don't require auth. you give output in few lines",
    tools=[http_request]
) 

@app.entrypoint
def invoke(payload):
    """Your AI agent function"""
    
    # Get the user's prompt from the payload
    user_message = payload.get("prompt", "Hello! How can i help you today?")

    result = agent(user_message)

    return {"result": result.message}

if __name__ == "__main__":
    print("Agent is running on 0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080)
