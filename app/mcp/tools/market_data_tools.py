"""
行情数据 MCP 工具
"""
from typing import Optional
from app.utils import get_logger

logger = get_logger(__name__)


def register_market_data_tools(mcp):
    """Register market data tools with the MCP server"""

    @mcp.tool()
    def get_stock_data(
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        market: str = "CN"
    ) -> dict:
        """
        查询股票历史行情数据和期间统计

        Args:
            stock_code: 股票代码（如 600000）
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
            market: 市场（默认 CN，当前仅支持A股）

        Returns:
            包含 records 和 summary 的行情数据
        """
        from app.services import get_watchlist_service
        result = get_watchlist_service().get_stock_data_with_indicators(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            ma_periods=[5, 30, 60]
        )
        # Return only records + summary (not indicators)
        return {
            "stock_code": result["stock_code"],
            "records": result["records"],
            "summary": result["summary"]
        }

    @mcp.tool()
    def get_stock_indicators(
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ma_periods: str = "5,30,60"
    ) -> dict:
        """
        查询股票技术指标（移动均线）

        Args:
            stock_code: 股票代码（如 600000）
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
            ma_periods: 均线周期，逗号分隔（默认 "5,30,60"）

        Returns:
            包含各期均线数据的指标
        """
        periods = [int(p.strip()) for p in ma_periods.split(',') if p.strip()]

        from app.services import get_watchlist_service
        result = get_watchlist_service().get_stock_data_with_indicators(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            ma_periods=periods
        )
        # Return only indicators
        return {
            "stock_code": result["stock_code"],
            "indicators": result["indicators"]
        }
