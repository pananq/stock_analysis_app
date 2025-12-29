#!/usr/bin/env python3
"""
数据回填脚本 - 为现有股票数据回填earliest_data_date和latest_data_date字段
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.orm_models import ORMDatabase
from app.utils import get_logger, get_config
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

logger = get_logger(__name__)


def backfill_date_ranges(batch_size: int = 100, verbose: bool = True):
    """
    回填所有股票的数据时间范围
    
    Args:
        batch_size: 每次处理的股票数量
        verbose: 是否显示详细信息
    
    Returns:
        dict: 处理结果统计
    """
    logger.info("=" * 60)
    logger.info("开始回填股票数据时间范围")
    logger.info("=" * 60)
    
    try:
        # 获取配置
        config = get_config()
        mysql_config = config.get('database.mysql')
        
        if not mysql_config:
            raise ValueError("未配置MySQL数据库信息")
        
        # 构建数据库连接URL
        mysql_url = (
            f"mysql+pymysql://{mysql_config.get('username')}:"
            f"{mysql_config.get('password')}@"
            f"{mysql_config.get('host')}:"
            f"{mysql_config.get('port')}/"
            f"{mysql_config.get('database')}?charset=utf8mb4"
        )
        
        # 创建数据库连接
        orm_db = ORMDatabase(mysql_url)
        Session = sessionmaker(bind=orm_db.engine)
        
        # 导入模型
        from app.models.orm_models import Stock, DailyMarket
        
        session = Session()
        
        try:
            # 获取所有股票
            query = session.query(Stock.code, Stock.name).filter(Stock.status == 'normal')
            total_stocks = query.count()
            
            logger.info(f"共 {total_stocks} 只股票需要处理")
            
            if total_stocks == 0:
                logger.info("没有需要处理的股票")
                return {
                    'success': True,
                    'total_stocks': 0,
                    'updated_stocks': 0,
                    'skipped_stocks': 0,
                    'failed_stocks': 0
                }
            
            # 统计信息
            updated_count = 0
            skipped_count = 0
            failed_count = 0
            failed_stocks = []
            
            # 分批处理
            offset = 0
            while offset < total_stocks:
                # 获取一批股票
                stocks = query.offset(offset).limit(batch_size).all()
                
                for stock in stocks:
                    code = stock.code
                    name = stock.name
                    
                    try:
                        # 查询该股票的最早和最晚数据日期
                        date_range = session.query(
                            func.min(DailyMarket.trade_date).label('earliest_date'),
                            func.max(DailyMarket.trade_date).label('latest_date')
                        ).filter(DailyMarket.code == code).first()
                        
                        if date_range and date_range.earliest_date and date_range.latest_date:
                            # 更新股票的时间范围
                            stock_to_update = session.query(Stock).filter(Stock.code == code).first()
                            if stock_to_update:
                                stock_to_update.earliest_data_date = date_range.earliest_date
                                stock_to_update.latest_data_date = date_range.latest_date
                                stock_to_update.updated_at = datetime.now()
                                updated_count += 1
                                
                                if verbose:
                                    logger.info(f"✓ {code} - {name}: {date_range.earliest_date} ~ {date_range.latest_date}")
                        else:
                            # 没有数据
                            skipped_count += 1
                            if verbose:
                                logger.debug(f"跳过 {code} - {name}: 无历史数据")
                    
                    except Exception as e:
                        failed_count += 1
                        failed_stocks.append({'code': code, 'name': name, 'reason': str(e)})
                        logger.error(f"✗ {code} - {name}: {e}")
                
                # 提交当前批次
                session.commit()
                offset += batch_size
                
                # 显示进度
                progress = min(offset, total_stocks)
                logger.info(f"进度: {progress}/{total_stocks} ({progress/total_stocks*100:.1f}%)")
            
            # 输出统计结果
            logger.info("=" * 60)
            logger.info("回填完成")
            logger.info(f"总股票数: {total_stocks}")
            logger.info(f"已更新: {updated_count}")
            logger.info(f"已跳过: {skipped_count}")
            logger.info(f"失败: {failed_count}")
            logger.info("=" * 60)
            
            if failed_stocks:
                logger.warning(f"失败的股票列表（前10个）:")
                for stock in failed_stocks[:10]:
                    logger.warning(f"  {stock['code']} - {stock['name']}: {stock['reason']}")
            
            return {
                'success': True,
                'total_stocks': total_stocks,
                'updated_stocks': updated_count,
                'skipped_stocks': skipped_count,
                'failed_stocks': failed_count,
                'failed_list': failed_stocks
            }
        
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"回填失败: {e}", exc_info=True)
        logger.info("=" * 60)
        logger.info("回填失败！")
        logger.info("=" * 60)
        return {
            'success': False,
            'error': str(e)
        }


def backfill_single_stock(stock_code: str):
    """
    回填单只股票的数据时间范围
    
    Args:
        stock_code: 股票代码
    
    Returns:
        dict: 处理结果
    """
    logger.info(f"开始回填股票 {stock_code} 的数据时间范围")
    
    try:
        # 获取配置
        config = get_config()
        mysql_config = config.get('database.mysql')
        
        if not mysql_config:
            raise ValueError("未配置MySQL数据库信息")
        
        # 构建数据库连接URL
        mysql_url = (
            f"mysql+pymysql://{mysql_config.get('username')}:"
            f"{mysql_config.get('password')}@"
            f"{mysql_config.get('host')}:"
            f"{mysql_config.get('port')}/"
            f"{mysql_config.get('database')}?charset=utf8mb4"
        )
        
        # 创建数据库连接
        orm_db = ORMDatabase(mysql_url)
        Session = sessionmaker(bind=orm_db.engine)
        
        # 导入模型
        from app.models.orm_models import Stock, DailyMarket
        
        session = Session()
        
        try:
            # 查询股票信息
            stock = session.query(Stock).filter(Stock.code == stock_code).first()
            
            if not stock:
                logger.error(f"未找到股票: {stock_code}")
                return {
                    'success': False,
                    'error': f'未找到股票: {stock_code}'
                }
            
            # 查询该股票的最早和最晚数据日期
            date_range = session.query(
                func.min(DailyMarket.trade_date).label('earliest_date'),
                func.max(DailyMarket.trade_date).label('latest_date')
            ).filter(DailyMarket.code == stock_code).first()
            
            if date_range and date_range.earliest_date and date_range.latest_date:
                # 更新股票的时间范围
                stock.earliest_data_date = date_range.earliest_date
                stock.latest_data_date = date_range.latest_date
                stock.updated_at = datetime.now()
                session.commit()
                
                logger.info(f"✓ {stock_code} - {stock.name}: {date_range.earliest_date} ~ {date_range.latest_date}")
                return {
                    'success': True,
                    'code': stock_code,
                    'name': stock.name,
                    'earliest_date': date_range.earliest_date.strftime('%Y-%m-%d'),
                    'latest_date': date_range.latest_date.strftime('%Y-%m-%d')
                }
            else:
                logger.info(f"股票 {stock_code} 没有历史数据")
                return {
                    'success': True,
                    'code': stock_code,
                    'name': stock.name,
                    'message': '没有历史数据'
                }
        
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"回填失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='股票数据时间范围回填工具')
    parser.add_argument('--stock', type=str, help='指定单只股票代码进行回填')
    parser.add_argument('--batch-size', type=int, default=100, help='每批处理的股票数量（默认100）')
    parser.add_argument('--quiet', action='store_true', help='静默模式，不显示详细信息')
    
    args = parser.parse_args()
    
    if args.stock:
        # 回填单只股票
        result = backfill_single_stock(args.stock)
    else:
        # 回填所有股票
        result = backfill_date_ranges(batch_size=args.batch_size, verbose=not args.quiet)
    
    sys.exit(0 if result['success'] else 1)
