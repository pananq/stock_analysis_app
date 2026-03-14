"""
MCP 服务器
使用 FastMCP 提供 SSE 传输的 MCP 服务
"""
from contextvars import ContextVar
from typing import Optional
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from app.utils import get_logger, get_config

logger = get_logger(__name__)

# Context variable to store authenticated user_id per connection
current_user_id: ContextVar[Optional[int]] = ContextVar('current_user_id', default=None)


class BearerTokenMiddleware:
    """
    纯 ASGI 中间件，从 Authorization: Bearer <token> 头提取 token，
    验证后将 user_id 写入 current_user_id contextvar。
    必须使用纯 ASGI 中间件（而非 BaseHTTPMiddleware），确保 ContextVar
    在同一 asyncio Task 内传播到 SSE 长连接的工具调用中。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            auth_header = headers.get(b"authorization", b"").decode("utf-8", errors="ignore")
            if auth_header.lower().startswith("bearer "):
                token = auth_header[7:]
                await self._verify_and_set(token)
        await self.app(scope, receive, send)

    async def _verify_and_set(self, token: str):
        try:
            from app.services.api_token_service import get_api_token_service
            service = get_api_token_service()
            result = service.verify_token(token)
            if result:
                user_id = result.get('user_id')
                if user_id:
                    current_user_id.set(user_id)
                    logger.debug(f"MCP 认证成功，user_id={user_id}")
        except Exception as e:
            logger.error(f"Token 验证失败: {e}")


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
        transport_security=transport_security,
    )

    # Register tools from tool modules
    from app.mcp.tools.watchlist_tools import register_watchlist_tools
    from app.mcp.tools.market_data_tools import register_market_data_tools
    register_watchlist_tools(mcp)
    register_market_data_tools(mcp)

    return mcp


def run_mcp_server():
    """Run the MCP server (called as multiprocessing target)"""
    import uvicorn
    import anyio
    from app.utils import get_config, setup_logging

    config = get_config()
    setup_logging(config)

    logger.info("MCP 服务器启动中...")

    mcp = create_mcp_server()

    mcp_config = config.get('mcp', {})
    host = mcp_config.get('host', '0.0.0.0')
    port = mcp_config.get('port', 5002)

    logger.info(f"MCP 服务器启动: http://{host}:{port}/sse")

    # 使用纯 ASGI 中间件包装，确保 ContextVar 在 SSE 长连接中正确传播
    starlette_app = mcp.sse_app()
    app_with_auth = BearerTokenMiddleware(starlette_app)

    async def serve():
        config_uv = uvicorn.Config(
            app_with_auth,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config_uv)
        await server.serve()

    anyio.run(serve)
