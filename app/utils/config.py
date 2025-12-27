"""
配置管理模块
负责读取、验证和管理系统配置
"""
import os
import yaml
from typing import Dict, Any
from pathlib import Path


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为项目根目录下的config.yaml
        """
        if config_path is None:
            # 获取项目根目录（app/utils -> app -> project_root）
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            # 应用环境变量覆盖
            self._apply_env_overrides()
            
            # 验证配置
            self._validate_config()
            
            # 处理相对路径
            self._resolve_paths()
            
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖配置文件中的配置"""
        # MySQL配置的环境变量覆盖
        env_mappings = {
            'MYSQL_HOST': ('database', 'mysql', 'host'),
            'MYSQL_PORT': ('database', 'mysql', 'port'),
            'MYSQL_DATABASE': ('database', 'mysql', 'database'),
            'MYSQL_USER': ('database', 'mysql', 'username'),
            'MYSQL_PASSWORD': ('database', 'mysql', 'password'),
        }
        
        for env_key, config_path in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                # 特殊处理：将字符串端口号转换为整数
                if env_key == 'MYSQL_PORT':
                    try:
                        env_value = int(env_value)
                    except ValueError:
                        continue
                
                # 导航到配置字典的指定路径
                config = self.config
                for key in config_path[:-1]:
                    if key not in config:
                        config[key] = {}
                    config = config[key]
                
                # 设置配置值
                config[config_path[-1]] = env_value
    
    def _validate_config(self):
        """验证配置参数的有效性"""
        # 验证数据源配置
        datasource_type = self.config.get('datasource', {}).get('type')
        if datasource_type not in ['akshare', 'tushare']:
            raise ValueError(f"不支持的数据源类型: {datasource_type}")
        
        if datasource_type == 'tushare':
            # 支持两种配置格式: datasource.tushare.token 或 datasource.tushare_token
            token = self.config.get('datasource', {}).get('tushare', {}).get('token')
            if not token:
                token = self.config.get('datasource', {}).get('tushare_token')
            if not token:
                raise ValueError("使用tushare数据源时必须配置tushare_token")
        
        # 验证API频率限制
        rate_limit = self.config.get('api_rate_limit', {})
        min_delay = rate_limit.get('min_delay', 0.1)
        max_delay = rate_limit.get('max_delay', 0.3)
        if min_delay > max_delay:
            raise ValueError("min_delay不能大于max_delay")
        
        # 验证Web服务端口
        port = self.config.get('web', {}).get('port', 5000)
        if not (1024 <= port <= 65535):
            raise ValueError(f"端口号必须在1024-65535之间: {port}")
        
        # 验证日志级别
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level not in valid_levels:
            raise ValueError(f"无效的日志级别: {log_level}")
        
        # 验证数据库配置
        db_config = self.config.get('database', {})
        db_type = db_config.get('type', 'mysql')
        
        if db_type != 'mysql':
            raise ValueError(f"不支持的数据库类型: {db_type}，只支持mysql")
    
    def _resolve_paths(self):
        """将相对路径转换为绝对路径"""
        project_root = self.config_path.parent
        
        # 数据库路径
        db_config = self.config.get('database', {})
        for key in ['duckdb_path']:
            if key in db_config:
                path = Path(db_config[key])
                if not path.is_absolute():
                    db_config[key] = str(project_root / path)
        
        # 日志文件路径
        log_config = self.config.get('logging', {})
        if 'file_path' in log_config:
            path = Path(log_config['file_path'])
            if not path.is_absolute():
                log_config['file_path'] = str(project_root / path)
        
        # 备份目录
        data_mgmt = self.config.get('data_management', {})
        if 'backup_dir' in data_mgmt:
            path = Path(data_mgmt['backup_dir'])
            if not path.is_absolute():
                data_mgmt['backup_dir'] = str(project_root / path)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置键，支持点号分隔的多级键，如 'datasource.type'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        设置配置项
        
        Args:
            key: 配置键，支持点号分隔的多级键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            raise IOError(f"保存配置文件失败: {e}")
    
    def reload(self):
        """重新加载配置文件"""
        self._load_config()
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self.config.copy()


# 全局配置实例
_config_instance = None


def get_config(config_path: str = None) -> ConfigManager:
    """
    获取全局配置实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        ConfigManager实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager(config_path)
    return _config_instance
