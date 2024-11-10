from abc import ABC, abstractmethod
from typing import List
from ..models.proxy import Proxy

class BaseTester(ABC):
    """代理测试器的基类"""
    
    _logger = None  # 类级别的logger
    
    def __init__(self, logger=None):
        self.logger = logger
        self.__class__._logger = logger  # 设置类级别的logger
    
    @abstractmethod
    async def test(self, proxy: Proxy, target_host: str) -> bool:
        """测试代理是否可用"""
        pass 