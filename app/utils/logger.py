"""
日志管理模块
提供统一的日志记录功能
"""
import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """对常见凭据格式做日志脱敏。"""

    PATTERNS = (
        (
            re.compile(r'([a-z][a-z0-9+.-]*://[^:/@\s]+:)([^@\s]+)(@)', re.I),
            r'\1***\3',
        ),
        (
            re.compile(r'(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+'),
            r'\1***',
        ),
        (
            re.compile(
                r'(?i)\b(password|api[_-]?key|secret|token)\b'
                r'(\s*[:=]\s*)'
                r'([^\s,;]+)'
            ),
            r'\1\2***',
        ),
    )

    @classmethod
    def redact(cls, value) -> str:
        text = str(value)
        for pattern, replacement in cls.PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: self.redact(value) if isinstance(value, str) else value
                    for key, value in record.args.items()
                }
            else:
                record.args = tuple(
                    self.redact(value) if isinstance(value, str) else value
                    for value in record.args
                )
        return True


class RedactingFormatter(logging.Formatter):
    """连同异常堆栈一起脱敏最终日志文本。"""

    def format(self, record: logging.LogRecord) -> str:
        return SensitiveDataFilter.redact(super().format(record))


class ErrorTolerantRotatingFileHandler(RotatingFileHandler):
    """
    容错的日志文件处理器
    当文件写入失败时，不会导致程序崩溃，而是静默失败
    """
    def emit(self, record):
        try:
            super().emit(record)
        except (OSError, IOError) as e:
            # 静默处理文件写入错误，避免影响程序运行
            # 可以在这里添加额外的错误通知逻辑
            pass
        except Exception:
            # 其他异常也静默处理
            pass


class LoggerManager:
    """日志管理器"""
    
    _loggers = {}
    _initialized = False
    
    @classmethod
    def setup(cls, log_file: str, level: str = 'INFO', 
              max_bytes: int = 10*1024*1024, backup_count: int = 30,
              log_format: str = None):
        """
        初始化日志系统
        
        Args:
            log_file: 日志文件路径
            level: 日志级别
            max_bytes: 单个日志文件最大大小（字节）
            backup_count: 保留的日志文件数量
            log_format: 日志格式
        """
        if cls._initialized:
            return
        
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 设置日志格式
        if log_format is None:
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        formatter = RedactingFormatter(log_format)
        
        # 创建容错的文件处理器（支持日志轮转）
        file_handler = ErrorTolerantRotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveDataFilter())
        
        # 创建容错的控制台处理器
        class ErrorTolerantStreamHandler(logging.StreamHandler):
            """容错的控制台处理器"""
            def emit(self, record):
                try:
                    super().emit(record)
                except (OSError, IOError, BrokenPipeError):
                    # 静默处理输出错误，避免影响程序运行
                    pass
                except Exception:
                    # 其他异常也静默处理
                    pass
        
        console_handler = ErrorTolerantStreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(SensitiveDataFilter())
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper()))
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # 禁用日志传播错误，避免级联失败
        root_logger.raiseExceptions = False
        
        cls._initialized = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称，通常使用模块名
            
        Returns:
            Logger实例
        """
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(name)
            cls._loggers[name].addFilter(SensitiveDataFilter())
        return cls._loggers[name]


def setup_logging(config):
    """
    根据配置初始化日志系统
    
    Args:
        config: 配置管理器实例
    """
    log_config = config.get('logging', {})
    
    LoggerManager.setup(
        log_file=log_config.get(
            'file_path',
            log_config.get('file', './logs/app.log')
        ),
        level=log_config.get('level', 'INFO'),
        max_bytes=log_config.get(
            'max_file_size',
            log_config.get('max_bytes', 10)
        ) * 1024 * 1024,
        backup_count=log_config.get('backup_count', 30),
        log_format=log_config.get('format')
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器的便捷函数
    
    Args:
        name: 日志记录器名称
        
    Returns:
        Logger实例
    """
    return LoggerManager.get_logger(name)
