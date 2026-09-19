from typing import Optional, Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent, GetPromptResult, ReadResourceResult, Resource, TextResourceContents, BlobResourceContents, Prompt
from pydantic import AnyUrl


class MCPClient:
    """Handles MCP server connection and tool execution"""

    def __init__(self, mcp_server_url: str) -> None:
        self.mcp_server_url = mcp_server_url
        self.session: Optional[ClientSession] = None
        self._streams_context = None
        self._session_context = None

    async def __aenter__(self):
        self._streams_context = streamablehttp_client(self.mcp_server_url)
        read_stream, write_stream, _ = await self._streams_context.__aenter__()
        self._session_context = ClientSession(read_stream, write_stream)
        self.session = await self._session_context.__aenter__()
        print(f"MCP server initialized: {await self.session.initialize()}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session is not None and self._session_context is not None:
            await self._session_context.__aexit__(exc_type, exc_val, exc_tb)
            self.session = None
        if self._streams_context is not None:
            await self._streams_context.__aexit__(exc_type, exc_val, exc_tb)
            self._streams_context = None

    async def get_tools(self) -> list[dict[str, Any]]:
        """Get available tools from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected. Call connect() first.")
        tools = await self.session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools.tools
        ]

    async def call_tool(self, tool_name: str, tool_args: dict[str, Any]) -> Any:
        """Call a specific tool on the MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected. Call connect() first.")

        tool_result: CallToolResult = await self.session.call_tool(tool_name, tool_args)
        if not tool_result.content:
            return ""
        content = tool_result.content[0]
        print(f"    Tool result: {content}\n")
        return content.text if isinstance(content, TextContent) else content

    async def get_resources(self) -> list[Resource]:
        """Get available resources from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        try:
            return (await self.session.list_resources()).resources
        except Exception as error:
            print(f"Unable to list MCP resources: {error}")
            return []

    async def get_resource(self, uri: AnyUrl) -> str | bytes:
        """Get specific resource content"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")

        resource_result: ReadResourceResult = await self.session.read_resource(uri)
        if not resource_result.contents:
            return ""
        content = resource_result.contents[0]
        if isinstance(content, TextResourceContents):
            return content.text
        if isinstance(content, BlobResourceContents):
            return content.blob
        raise TypeError(f"Unsupported resource content: {type(content).__name__}")

    async def get_prompts(self) -> list[Prompt]:
        """Get available prompts from MCP server"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        try:
            return (await self.session.list_prompts()).prompts
        except Exception as error:
            print(f"Unable to list MCP prompts: {error}")
            return []

    async def get_prompt(self, name: str) -> str:
        """Get specific prompt content"""
        if not self.session:
            raise RuntimeError("MCP client not connected.")
        prompt_result: GetPromptResult = await self.session.get_prompt(name)
        combined_content = ""
        for message in prompt_result.messages:
            content = getattr(message, "content", None)
            if isinstance(content, TextContent):
                combined_content += content.text + "\n"
            elif isinstance(content, str):
                combined_content += content + "\n"
        return combined_content
