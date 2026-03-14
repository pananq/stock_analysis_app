"""
关注列表 MCP 工具
"""
from typing import Optional
from app.mcp.server import current_user_id
from app.utils import get_logger

logger = get_logger(__name__)


def register_watchlist_tools(mcp):
    """Register watchlist tools with the MCP server"""

    @mcp.tool()
    def get_watchlist(group: Optional[str] = None, tag: Optional[str] = None) -> dict:
        """
        获取当前用户的股票关注列表

        Args:
            group: 按分组名过滤（可选）
            tag: 按标签过滤（可选）

        Returns:
            关注列表
        """
        user_id = current_user_id.get()
        if user_id is None:
            return {"error": "未认证，请先配置 API Token"}

        from app.services import get_watchlist_service
        items = get_watchlist_service().get_watchlist(user_id, group_name=group, tag=tag)
        return {"success": True, "data": items, "count": len(items)}

    @mcp.tool()
    def add_to_watchlist(
        stock_code: str,
        market: str = "CN",
        group: Optional[str] = None,
        tags: Optional[str] = None,
        notes: Optional[str] = None
    ) -> dict:
        """
        添加股票到关注列表

        Args:
            stock_code: 股票代码（如 600000）
            market: 市场（默认 CN 表示A股）
            group: 分组名（可选，如"持仓"、"观察"）
            tags: 标签，逗号分隔（可选，如"银行,价值投资"）
            notes: 备注（可选）

        Returns:
            添加结果
        """
        user_id = current_user_id.get()
        if user_id is None:
            return {"error": "未认证，请先配置 API Token"}

        from app.services import get_watchlist_service
        result = get_watchlist_service().add_stock(
            user_id=user_id,
            stock_code=stock_code,
            market=market,
            group_name=group,
            tags=tags,
            notes=notes
        )
        return result

    @mcp.tool()
    def remove_from_watchlist(watchlist_id: int) -> dict:
        """
        从关注列表中移除股票

        Args:
            watchlist_id: 关注条目的 ID（从 get_watchlist 结果中获取）

        Returns:
            操作结果
        """
        user_id = current_user_id.get()
        if user_id is None:
            return {"error": "未认证，请先配置 API Token"}

        from app.services import get_watchlist_service
        success = get_watchlist_service().remove_stock(user_id, watchlist_id)
        return {"success": success}
