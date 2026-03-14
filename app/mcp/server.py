"""
MCP 服务器
使用 FastMCP 提供 SSE 传输的 MCP 服务
"""
import asyncio
from contextvars import ContextVar
from typing import Optional
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from app.utils import get_logger, get_config

logger = get_logger(__name__)

# Context variable to store authenticated user_id per connection
current_user_id: ContextVar[Optional[int]] = ContextVar('current_user_id', default=None)

def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server"""
    config = get_config()
    mcp_config = config.get('mcp', {})
    host = mcp_config.get('host', '0.0.0.0')
    port = mcp_config.get('port', 5002)

    # Disable DNS rebinding protection for non-localhost hosts
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )

    mcp = FastMCP(
        "stock-analysis",
        host=host,
        port=port,
        transport_security=transport_security
    )

    # Register tools from tool modules
    from app.mcp.tools.watchlist_tools import register_watchlist_tools
    from app.mcp.tools.market_data_tools import register_market_data_tools
    register_watchlist_tools(mcp)
    register_market_data_tools(mcp)

    return mcp


def run_mcp_server():
    """Run the MCP server (called as multiprocessing target)"""
    from app.utils import get_config, setup_logging
    config = get_config()
    setup_logging(config)

    logger.info("MCP 服务器启动中...")

    mcp = create_mcp_server()

    mcp_config = config.get('mcp', {})
    host = mcp_config.get('host', '0.0.0.0')
    port = mcp_config.get('port', 5002)

    logger.info(f"MCP 服务器启动: http://{host}:{port}/sse")

    mcp.run(transport='sse')
