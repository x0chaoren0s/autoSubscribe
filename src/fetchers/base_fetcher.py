from abc import ABC, abstractmethod
from typing import Dict

class BaseFetcher(ABC):
    """订阅源获取器的基类"""
    
    _logger = None  # 类级别的logger
    
    def __init__(self, logger=None, config: Dict = None):
        """
        初始化获取器
        
        Args:
            logger: 日志记录器
            config: 配置字典，包含以下结构：
                {
                    'fetcher': {
                        'timeout': int,        # 连接超时
                        'retry_times': int,    # 重试次数
                        'user_agent': str,     # User-Agent
                        ...                    # 其他配置
                    }
                }
        """
        self.logger = logger
        self.__class__._logger = logger  # 设置类级别的logger
        
        # 获取配置
        self.config = config or {}
        fetcher_config = self.config.get('fetcher', {})
        
        # 设置基本参数
        self.timeout = fetcher_config.get('timeout', 10)
        self.retry_times = fetcher_config.get('retry_times', 3)
        self.user_agent = fetcher_config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
    
    @abstractmethod
    async def fetch(self, url: str) -> str:
        """获取订阅内容"""
        pass
    
    def get_config(self, key: str, default=None):
        """获取获取器的特定配置"""
        return self.config.get('fetcher', {}).get(key, default)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        pass