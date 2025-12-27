"""
策略配置管理服务

提供策略的创建、编辑、删除、查询等功能
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from app.models.database_factory import get_database
from app.utils import get_logger

logger = get_logger(__name__)


class StrategyService:
    """策略配置管理服务"""
    
    def __init__(self):
        """初始化策略服务"""
        self.db = get_database()
        logger.info("策略服务初始化完成")
    
    def create_strategy(self, name: str, description: str = "", 
                       rise_threshold: float = 8.0,
                       observation_days: int = 3,
                       ma_period: int = 5,
                       enabled: bool = True) -> Optional[int]:
        """
        创建新策略
        
        Args:
            name: 策略名称
            description: 策略描述
            rise_threshold: 涨幅阈值（百分比），默认8.0，范围0.01-20.0
            observation_days: 观察天数，默认3天，范围1-30
            ma_period: 均线周期，默认5日，支持5/10/20/30/60
            enabled: 是否启用，默认True
            
        Returns:
            策略ID，如果创建失败返回None
        """
        try:
            # 验证参数
            if not name or not name.strip():
                logger.error("策略名称不能为空")
                return None
            
            # 验证涨幅阈值
            if not (0.01 <= rise_threshold <= 20.0):
                logger.error(f"涨幅阈值必须在0.01-20.0之间，当前值: {rise_threshold}")
                return None
            
            # 验证观察天数
            if not (1 <= observation_days <= 30):
                logger.error(f"观察天数必须在1-30之间，当前值: {observation_days}")
                return None
            
            # 验证均线周期
            valid_ma_periods = [5, 10, 20, 30, 60]
            if ma_period not in valid_ma_periods:
                logger.error(f"均线周期必须是{valid_ma_periods}之一，当前值: {ma_period}")
                return None
            
            # 检查策略名称是否已存在
            existing = self.db.execute_query(
                "SELECT id FROM strategies WHERE name = ?",
                (name.strip(),)
            )
            
            if existing:
                logger.error(f"策略名称已存在: {name}")
                return None
            
            # 构建策略配置JSON
            config = {
                "rise_threshold": rise_threshold,
                "observation_days": observation_days,
                "ma_period": ma_period
            }
            
            # 插入策略
            sql = """
                INSERT INTO strategies (name, description, config, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.db.execute_update(
                sql,
                (name.strip(), description.strip(), json.dumps(config), 
                 1 if enabled else 0, now, now)
            )
            
            # 获取新创建的策略ID
            result = self.db.execute_query(
                "SELECT id FROM strategies WHERE name = ?",
                (name.strip(),)
            )
            
            if result:
                strategy_id = result[0]['id']
                logger.info(f"策略创建成功: {name} (ID: {strategy_id})")
                return strategy_id
            
            return None
            
        except Exception as e:
            logger.error(f"创建策略失败: {e}")
            return None
    
    def update_strategy(self, strategy_id: int, name: Optional[str] = None,
                       description: Optional[str] = None,
                       rise_threshold: Optional[float] = None,
                       observation_days: Optional[int] = None,
                       ma_period: Optional[int] = None,
                       enabled: Optional[bool] = None) -> bool:
        """
        更新策略
        
        Args:
            strategy_id: 策略ID
            name: 策略名称（可选）
            description: 策略描述（可选）
            rise_threshold: 涨幅阈值（可选）
            observation_days: 观察天数（可选）
            ma_period: 均线周期（可选）
            enabled: 是否启用（可选）
            
        Returns:
            是否更新成功
        """
        try:
            # 获取现有策略
            strategy = self.get_strategy(strategy_id)
            if not strategy:
                logger.error(f"策略不存在: {strategy_id}")
                return False
            
            # 获取现有配置（已经是字典格式）
            config = strategy['config']
            
            # 更新字段
            update_fields = []
            params = []
            
            if name is not None:
                if not name.strip():
                    logger.error("策略名称不能为空")
                    return False
                
                # 检查名称是否与其他策略冲突
                existing = self.db.execute_query(
                    "SELECT id FROM strategies WHERE name = ? AND id != ?",
                    (name.strip(), strategy_id)
                )
                if existing:
                    logger.error(f"策略名称已存在: {name}")
                    return False
                
                update_fields.append("name = ?")
                params.append(name.strip())
            
            if description is not None:
                update_fields.append("description = ?")
                params.append(description.strip())
            
            # 更新配置参数
            config_updated = False
            
            if rise_threshold is not None:
                if not (0.01 <= rise_threshold <= 20.0):
                    logger.error(f"涨幅阈值必须在0.01-20.0之间，当前值: {rise_threshold}")
                    return False
                config['rise_threshold'] = rise_threshold
                config_updated = True
            
            if observation_days is not None:
                if not (1 <= observation_days <= 30):
                    logger.error(f"观察天数必须在1-30之间，当前值: {observation_days}")
                    return False
                config['observation_days'] = observation_days
                config_updated = True
            
            if ma_period is not None:
                valid_ma_periods = [5, 10, 20, 30, 60]
                if ma_period not in valid_ma_periods:
                    logger.error(f"均线周期必须是{valid_ma_periods}之一，当前值: {ma_period}")
                    return False
                config['ma_period'] = ma_period
                config_updated = True
            
            if config_updated:
                update_fields.append("config = ?")
                params.append(json.dumps(config))
            
            if enabled is not None:
                update_fields.append("enabled = ?")
                params.append(1 if enabled else 0)
            
            if not update_fields:
                logger.warning("没有需要更新的字段")
                return True
            
            # 添加更新时间
            update_fields.append("updated_at = ?")
            params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # 添加WHERE条件
            params.append(strategy_id)
            
            # 执行更新
            sql = f"UPDATE strategies SET {', '.join(update_fields)} WHERE id = ?"
            self.db.execute_update(sql, tuple(params))
            
            logger.info(f"策略更新成功: ID={strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新策略失败: {e}")
            return False
    
    def delete_strategy(self, strategy_id: int) -> bool:
        """
        删除策略
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            是否删除成功
        """
        try:
            # 检查策略是否存在
            strategy = self.get_strategy(strategy_id)
            if not strategy:
                logger.error(f"策略不存在: {strategy_id}")
                return False
            
            # 删除策略执行结果
            self.db.execute_update(
                "DELETE FROM strategy_results WHERE strategy_id = ?",
                (strategy_id,)
            )
            
            # 删除策略
            self.db.execute_update(
                "DELETE FROM strategies WHERE id = ?",
                (strategy_id,)
            )
            
            logger.info(f"策略删除成功: {strategy['name']} (ID: {strategy_id})")
            return True
            
        except Exception as e:
            logger.error(f"删除策略失败: {e}")
            return False
    
    def get_strategy(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """
        获取策略详情
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            策略信息字典，如果不存在返回None
        """
        try:
            result = self.db.execute_query(
                "SELECT * FROM strategies WHERE id = ?",
                (strategy_id,)
            )
            
            if result:
                strategy = dict(result[0])
                # 解析配置JSON
                strategy['config'] = json.loads(strategy['config'])
                strategy['enabled'] = bool(strategy['enabled'])
                return strategy
            
            return None
            
        except Exception as e:
            logger.error(f"获取策略失败: {e}")
            return None
    
    def list_strategies(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """
        获取策略列表
        
        Args:
            enabled_only: 是否只返回启用的策略
            
        Returns:
            策略列表
        """
        try:
            if enabled_only:
                sql = "SELECT * FROM strategies WHERE enabled = 1 ORDER BY created_at DESC"
                result = self.db.execute_query(sql)
            else:
                sql = "SELECT * FROM strategies ORDER BY created_at DESC"
                result = self.db.execute_query(sql)
            
            strategies = []
            for row in result:
                strategy = dict(row)
                # 解析配置JSON
                strategy['config'] = json.loads(strategy['config'])
                strategy['enabled'] = bool(strategy['enabled'])
                strategies.append(strategy)
            
            logger.info(f"获取策略列表成功，共 {len(strategies)} 条")
            return strategies
            
        except Exception as e:
            logger.error(f"获取策略列表失败: {e}")
            return []
    
    def get_strategy_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取策略
        
        Args:
            name: 策略名称
            
        Returns:
            策略信息字典，如果不存在返回None
        """
        try:
            result = self.db.execute_query(
                "SELECT * FROM strategies WHERE name = ?",
                (name.strip(),)
            )
            
            if result:
                strategy = dict(result[0])
                strategy['config'] = json.loads(strategy['config'])
                strategy['enabled'] = bool(strategy['enabled'])
                return strategy
            
            return None
            
        except Exception as e:
            logger.error(f"获取策略失败: {e}")
            return None
    
    def update_last_execution(self, strategy_id: int) -> bool:
        """
        更新策略的最后执行时间
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            是否更新成功
        """
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db.execute_update(
                "UPDATE strategies SET last_executed_at = ? WHERE id = ?",
                (now, strategy_id)
            )
            
            logger.debug(f"更新策略最后执行时间: ID={strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新策略最后执行时间失败: {e}")
            return False
    
    def validate_strategy_config(self, rise_threshold: float, 
                                observation_days: int, 
                                ma_period: int) -> tuple[bool, str]:
        """
        验证策略配置参数
        
        Args:
            rise_threshold: 涨幅阈值
            observation_days: 观察天数
            ma_period: 均线周期
            
        Returns:
            (是否有效, 错误信息)
        """
        # 验证涨幅阈值
        if not (0.01 <= rise_threshold <= 20.0):
            return False, f"涨幅阈值必须在0.01-20.0之间，当前值: {rise_threshold}"
        
        # 验证观察天数
        if not (1 <= observation_days <= 30):
            return False, f"观察天数必须在1-30之间，当前值: {observation_days}"
        
        # 验证均线周期
        valid_ma_periods = [5, 10, 20, 30, 60]
        if ma_period not in valid_ma_periods:
            return False, f"均线周期必须是{valid_ma_periods}之一，当前值: {ma_period}"
        
        return True, ""


# 全局策略服务实例
_strategy_service = None


def get_strategy_service() -> StrategyService:
    """获取策略服务实例（单例模式）"""
    global _strategy_service
    if _strategy_service is None:
        _strategy_service = StrategyService()
    return _strategy_service
