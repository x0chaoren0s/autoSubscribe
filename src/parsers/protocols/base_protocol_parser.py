from abc import ABC, abstractmethod
from ...models.proxy import Proxy
from ...utils.constants import SUPPORTED_PROTOCOLS

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
    
    def to_glider_url(self, proxy: Proxy) -> str:
        """转换为Glider URL格式（可选实现）"""
        return proxy.to_glider_url()