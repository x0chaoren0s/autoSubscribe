from abc import ABC, abstractmethod
from ...models.proxy import Proxy

class BaseProtocolParser(ABC):
    """协议解析器基类"""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    @abstractmethod
    def parse(self, line: str) -> Proxy:
        """解析协议特定的链接"""
        pass
    
    @classmethod
    @abstractmethod
    def protocol_prefix(cls) -> str:
        """返回协议的URL前缀"""
        pass 