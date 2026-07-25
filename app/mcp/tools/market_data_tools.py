"""
行情数据 MCP 工具
"""
from typing import Optional
from app.utils import get_logger
from app.mcp.server import current_user_id

logger = get_logger(__name__)


def register_market_data_tools(mcp):
    """Register market data tools with the MCP server"""

    @mcp.tool()
    def get_stock_data(
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        market: str = "CN",
        security_type: str = "STOCK"
    ) -> dict:
        """
        查询股票历史行情数据和期间统计

        Args:
            stock_code: 股票代码（如 600000）
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
            market: 市场（CN/HK/US）
            security_type: 证券类型（STOCK/ETF/FUND/INDEX）

        Returns:
            包含 records 和 summary 的行情数据
        """
        if current_user_id.get() is None:
            return {"error": "未认证，请先配置 API Token"}
        from app.services import get_watchlist_service
        result = get_watchlist_service().get_stock_data_with_indicators(
            stock_code=stock_code,
            market=market,
            security_type=security_type,
            start_date=start_date,
            end_date=end_date,
            ma_periods=[5, 30, 60]
        )
        # Return only records + summary (not indicators)
        return {
            "stock_code": result["stock_code"],
            "market": result["market"],
            "currency": result["currency"],
            "records": result["records"],
            "summary": result["summary"]
        }

    @mcp.tool()
    def get_stock_indicators(
        stock_code: str,
        market: str = "CN",
        security_type: str = "STOCK",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ma_periods: str = "5,30,60"
    ) -> dict:
        """
        查询股票技术指标（移动均线）

        Args:
            stock_code: 股票代码（如 600000）
            security_type: 证券类型（STOCK/ETF/FUND/INDEX）
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
            ma_periods: 均线周期，逗号分隔（默认 "5,30,60"）

        Returns:
            包含各期均线数据的指标
        """
        if current_user_id.get() is None:
            return {"error": "未认证，请先配置 API Token"}
        try:
            periods = [
                int(p.strip()) for p in ma_periods.split(',') if p.strip()
            ]
        except (AttributeError, ValueError):
            return {"error": "ma_periods 格式无效"}
        if (
            not periods
            or len(set(periods)) > 10
            or any(period < 1 or period > 250 for period in periods)
        ):
            return {"error": "均线周期必须为 1-250 之间的整数，且最多 10 个"}

        from app.services import get_watchlist_service
        result = get_watchlist_service().get_stock_data_with_indicators(
            stock_code=stock_code,
            market=market,
            security_type=security_type,
            start_date=start_date,
            end_date=end_date,
            ma_periods=periods
        )
        # Return only indicators
        return {
            "stock_code": result["stock_code"],
            "market": result["market"],
            "currency": result["currency"],
            "indicators": result["indicators"]
        }
