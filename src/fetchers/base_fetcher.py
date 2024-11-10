from abc import ABC, abstractmethod

class BaseFetcher(ABC):
    """订阅源获取器的基类"""
    
    _logger = None  # 类级别的logger
    
    def __init__(self, logger=None):
        self.logger = logger
        self.__class__._logger = logger  # 设置类级别的logger
    
    @abstractmethod
    async def fetch(self, url: str) -> str:
        """获取订阅内容"""
        pass 