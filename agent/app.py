import asyncio
import os

from agent.mcp_client import MCPClient
from agent.dial_client import DialClient
from agent.models.message import Message, Role
from agent.prompts import SYSTEM_PROMPT


# https://remote.mcpservers.org/fetch/mcp
# Pay attention that `fetch` doesn't have resources and prompts

async def main():
    api_key = os.getenv("DIAL_API_KEY")
    endpoint = os.getenv("DIAL_ENDPOINT")
    if not api_key or not endpoint:
        raise RuntimeError("Set DIAL_API_KEY and DIAL_ENDPOINT before starting the agent.")

    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8005/mcp")
    async with MCPClient(server_url) as mcp_client:
        resources = await mcp_client.get_resources()
        print(f"MCP resources: {[str(resource.uri) for resource in resources]}")

        tools = await mcp_client.get_tools()
        print(f"MCP tools: {[tool['function']['name'] for tool in tools]}")

        dial_client = DialClient(api_key, endpoint, tools, mcp_client)
        messages = [Message(role=Role.SYSTEM, content=SYSTEM_PROMPT)]

        for prompt in await mcp_client.get_prompts():
            prompt_content = await mcp_client.get_prompt(prompt.name)
            if prompt_content:
                messages.append(Message(role=Role.USER, content=prompt_content))

        print("Users Management Agent is ready. Type 'exit' to quit.")
        while True:
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.strip().lower() in {"exit", "quit"}:
                break
            if not user_input.strip():
                continue

            messages.append(Message(role=Role.USER, content=user_input))
            response = await dial_client.get_completion(messages)
            messages.append(response)


if __name__ == "__main__":
    asyncio.run(main())
