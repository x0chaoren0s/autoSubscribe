import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Union, Dict, List
from logging.handlers import RotatingFileHandler

class Logger:
    """日志管理器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化日志管理器
        
        Args:
            config: 配置字典，包含以下结构：
                {
                    'log': {
                        'level': str,          # 日志级别 (debug/info/warning/error)
                        'file': str,           # 日志文件路径
                        'console': bool,       # 是否输出到控制台
                        'format': str,         # 日志格式
                        'rotate': bool,        # 是否轮转日志
                        'max_size': str,       # 单个日志文件最大大小 (例如: "10M")
                        'keep': int           # 保留日志文件数量
                    }
                }
        """
        self.config = config or {}
        log_config = self.config.get('log', {})
        
        # 创建日志目录
        self.log_dir = Path(log_config.get('file', 'logs/autoSubscribe.log')).parent
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取日志配置
        self.log_level = self._get_log_level(log_config.get('level', 'info'))
        self.log_file = log_config.get('file', 'logs/autoSubscribe.log')
        self.console_output = log_config.get('console', True)
        self.log_format = log_config.get('format', '{time} {level}: {message}')
        self.rotate = log_config.get('rotate', True)
        self.max_size = self._parse_size(log_config.get('max_size', '10M'))
        self.keep_files = log_config.get('keep', 7)
        
        # 配置根日志记录器
        self.logger = logging.getLogger()
        self.logger.setLevel(self.log_level)
        
        # 移除所有已存在的处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 配置文件处理器
        if self.rotate:
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_size,
                backupCount=self.keep_files,
                encoding='utf-8'
            )
        else:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(self.log_level)
        self.logger.addHandler(file_handler)
        
        # 配置控制台处理器
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter('%(message)s')
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.INFO)
            self.logger.addHandler(console_handler)
        
        # 记录启动信息
        self.info("AutoSubscribe Started")
        self.debug(f"Log file: {self.log_file}")
    
    def _get_log_level(self, level: str) -> int:
        """获取日志级别"""
        levels = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR
        }
        return levels.get(level.lower(), logging.INFO)
    
    def _parse_size(self, size: str) -> int:
        """解析大小字符串（例如：10M）"""
        units = {'K': 1024, 'M': 1024*1024, 'G': 1024*1024*1024}
        if not size:
            return 10 * 1024 * 1024  # 默认10M
        
        size = size.upper()
        if size[-1] in units:
            return int(size[:-1]) * units[size[-1]]
        return int(size)
    
    def debug(self, msg: str):
        """调试信息（只写入文件）"""
        self.logger.debug(msg)
    
    def info(self, msg: str, end: str = '\n'):
        """普通信息（同时显示在控制台）"""
        # 如果是进度条信息，直接显示
        if msg.startswith('\r['):
            sys.stdout.write(msg)
            sys.stdout.flush()
            self.logger.debug(msg.replace('\r', ''))
            return
            
        # 如果是JSON或长文本，进行格式化
        if msg.startswith('{') or msg.startswith('['):
            try:
                formatted = json.dumps(json.loads(msg), indent=2, ensure_ascii=False)
                for line in formatted.split('\n'):
                    self.logger.info(line)
                return
            except:
                pass
                
        # 如果是分隔线，使用等号
        if msg.startswith('---'):
            self.logger.info('=' * 50)
            return
            
        # 如果是错误统计，使用特殊格式
        if "Failed to parse" in msg:
            if "Legacy encryption method" in msg:
                self.debug(msg)  # 只记录到文件
                return
            if "Unknown encryption method" in msg:
                self.debug(msg)  # 只记录到文件
                return
        
        # 其他信息正常显示
        if end == '\n':
            self.logger.info(msg)
        else:
            sys.stdout.write(msg + end)
            sys.stdout.flush()
            self.logger.debug(msg)
    
    def warning(self, msg: str):
        """警告信息"""
        self.logger.warning(msg)
    
    def error(self, msg: str):
        """错误信息"""
        # 如果是解析错误，只记录到debug日志
        if "Failed to parse" in msg:
            self.debug(msg)
            return
            
        # 其他错误正常显示
        self.logger.error(msg)
    
    def section(self, title: str):
        """添加一个分节标题"""
        if title == "Results":
            self.info("")
            return
        self.info(f"\n=== {title} ===")
    
    def separator(self, title: str, width: int = 20):
        """添加一个分隔线"""
        total_width = width
        title_width = len(title)
        left_width = (total_width - title_width) // 2
        right_width = total_width - title_width - left_width
        separator = "=" * left_width + title + "=" * right_width
        self.info(separator)
    
    def stats(self, title: str, stats: Dict[str, Union[int, Dict]]):
        """显示统计信息"""
        self.info(f"\n{title}:")
        for key, value in sorted(stats.items()):
            if isinstance(value, dict):
                self.info(f"  {key}:")
                for sub_key, sub_value in sorted(value.items()):
                    self.info(f"    {sub_key:<20}: {sub_value:>3} {'proxy' if sub_value == 1 else 'proxies'}")
            else:
                self.info(f"  {key:<10}: {value:>3} {'proxy' if value == 1 else 'proxies'}")
    
    def config_info(self, title: str, config_file: Path):
        """显示配置文件信息"""
        self.info(f"\n{title} config saved to: {config_file}")
        if config_file.suffix == '.json':
            with open(config_file, 'r', encoding='utf-8') as f:
                self.debug(f.read())  # JSON配置只记录到debug日志
        else:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.info("\nConfig content:")
                self.info("-" * 50)
                self.info(f.read())
                self.info("-" * 50)