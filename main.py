import logging
import os
import random

import requests
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

NAME = "demo-mcp-server"

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(NAME)

mcp = FastMCP(
    NAME,
    host=os.environ.get("HOST", "0.0.0.0"),
    port=int(os.environ.get("PORT", 8080)),
    streamable_http_path=os.environ.get("MCP_PATH", "/"),
)


# --- tools ---------------------------------------------------------------

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    logger.info(f"tool called: add({a}, {b})")
    return a + b


@mcp.tool()
def get_random_word() -> str:
    """Select random word from list"""
    logger.info("tool called: get_random_word()")
    return random.choice(["user", "admin", "root"])


@mcp.tool()
def get_current_weather(city: str) -> str:
    """Get current weather for a city"""
    logger.info(f"tool called: get_current_weather({city})")
    res = requests.get(f"https://wttr.in/{city}", timeout=10)
    res.raise_for_status()
    return res.json()


# --- plain HTTP bridge ---------------------------------------------------
# Lets tools be invoked with a simple GET, e.g.
#   http://127.0.0.1:8080/tool/add?a=10&b=1
# alongside the regular MCP streamable-http endpoint.

@mcp.custom_route("/tool/{tool_name}", methods=["GET"])
async def call_tool_http(request: Request) -> JSONResponse:
    tool_name = request.path_params["tool_name"]
    arguments = dict(request.query_params)
    logger.info(f"HTTP GET /tool/{tool_name} args={arguments}")
    try:
        _, structured = await mcp.call_tool(tool_name, arguments)
    except Exception as e:
        logger.error(f"tool call failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse(structured)


def main():
    logger.info(
        f"Starting {NAME} on {mcp.settings.host}:{mcp.settings.port} "
        f"(streamable-http, endpoint {mcp.settings.streamable_http_path})"
    )
    mcp.run("streamable-http")


if __name__ == "__main__":
    main()
