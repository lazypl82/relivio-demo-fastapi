from __future__ import annotations

import json
import os
import select
import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import Any


MCP_PROTOCOL_VERSION = "2025-03-26"


class McpClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class McpServerConfig:
    command: str
    api_url: str
    api_key: str


def build_mcp_server_config(api_url: str, api_key: str) -> McpServerConfig:
    return McpServerConfig(
        command=(os.getenv("RELIVIO_MCP_COMMAND") or "relivio-mcp").strip() or "relivio-mcp",
        api_url=api_url,
        api_key=api_key,
    )


class RelivioMcpClient:
    def __init__(self, config: McpServerConfig):
        self._config = config
        self._next_id = 1
        env = os.environ.copy()
        env["RELIVIO_API_URL"] = config.api_url
        env["RELIVIO_API_KEY"] = config.api_key
        self._process = subprocess.Popen(
            shlex.split(config.command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=env,
        )
        if self._process.stdin is None or self._process.stdout is None:
            raise McpClientError("Failed to open stdio pipes for relivio-mcp.")

    def close(self) -> None:
        if self._process.poll() is not None:
            return
        self._process.terminate()
        try:
            self._process.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=3.0)

    def __enter__(self) -> "RelivioMcpClient":
        self.initialize()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def initialize(self) -> dict[str, Any]:
        result = self.request(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "relivio-demo-fastapi",
                    "version": "0.1.0",
                },
            },
        )
        self.notify("initialized", {})
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        result = self.request("tools/list", {})
        tools = result.get("tools")
        if not isinstance(tools, list):
            raise McpClientError(f"Invalid tools/list response: {result}")
        return [tool for tool in tools if isinstance(tool, dict)]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        result = self.request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments or {},
            },
        )
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured

        content = result.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                text = block.get("text")
                if isinstance(text, str) and text.strip():
                    try:
                        parsed = json.loads(text)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(parsed, dict):
                        return parsed

        raise McpClientError(f"Invalid tools/call response: {result}")

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._write(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )
        return self._read_response(request_id)

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._write(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
        )

    def _write(self, payload: dict[str, Any]) -> None:
        if self._process.stdin is None:
            raise McpClientError("relivio-mcp stdin is unavailable.")
        self._process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self._process.stdin.flush()

    def _read_response(self, request_id: int) -> dict[str, Any]:
        deadline = time.monotonic() + 10.0
        if self._process.stdout is None:
            raise McpClientError("relivio-mcp stdout is unavailable.")

        while time.monotonic() < deadline:
            remaining = max(deadline - time.monotonic(), 0.0)
            ready, _, _ = select.select([self._process.stdout], [], [], remaining)
            if not ready:
                break

            line = self._process.stdout.readline()
            if line == "":
                if self._process.poll() is not None:
                    raise McpClientError("relivio-mcp exited before returning a response.")
                continue

            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise McpClientError(f"Invalid JSON from relivio-mcp: {line!r}") from exc

            if not isinstance(payload, dict):
                continue
            if payload.get("id") != request_id:
                continue
            if "error" in payload:
                raise McpClientError(f"MCP request failed: {payload['error']}")
            result = payload.get("result")
            if not isinstance(result, dict):
                raise McpClientError(f"Invalid MCP result payload: {payload}")
            return result

        raise McpClientError(f"Timed out waiting for MCP response to {request_id}.")


def list_recent_deployments_via_mcp(
    *,
    api_url: str,
    api_key: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    with RelivioMcpClient(build_mcp_server_config(api_url, api_key)) as client:
        tools = {tool.get("name") for tool in client.list_tools()}
        if "list_recent_deployments" not in tools:
            raise McpClientError("relivio-mcp is missing list_recent_deployments.")
        result = client.call_tool("list_recent_deployments", {"limit": limit})
    if result.get("status") != "ready":
        raise McpClientError(f"MCP recent deployments failed: {result}")
    deployments = result.get("deployments")
    if not isinstance(deployments, list):
        raise McpClientError(f"Invalid MCP recent deployments payload: {result}")
    return [item for item in deployments if isinstance(item, dict)]


def get_verdict_via_mcp(
    *,
    api_url: str,
    api_key: str,
    deployment_id: str | None = None,
) -> dict[str, Any]:
    with RelivioMcpClient(build_mcp_server_config(api_url, api_key)) as client:
        tools = {tool.get("name") for tool in client.list_tools()}
        if "get_verdict" not in tools:
            raise McpClientError("relivio-mcp is missing get_verdict.")
        arguments = {"deployment_id": deployment_id} if deployment_id else {}
        return client.call_tool("get_verdict", arguments)
