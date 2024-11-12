from typing import Dict, Type
from .base_protocol_parser import BaseProtocolParser
from ...utils.constants import SUPPORTED_PROTOCOLS

class ProtocolParserFactory:
    """协议解析器工厂"""
    
    _parsers: Dict[str, Type[BaseProtocolParser]] = {}
    _logger = None
    
    @classmethod
    def register(cls, parser_class: Type[BaseProtocolParser]):
        """注册解析器"""
        prefix = parser_class.protocol_prefix()
        protocol = prefix.rstrip('://')
        if protocol not in SUPPORTED_PROTOCOLS:
            raise ValueError(f"Unsupported protocol: {protocol}")
        cls._parsers[prefix] = parser_class
        return parser_class
    
    @classmethod
    def create_parser(cls, line: str) -> BaseProtocolParser:
        """创建解析器"""
        for prefix, parser_class in cls._parsers.items():
            if line.startswith(prefix):
                return parser_class(logger=cls._logger)
        raise ValueError(f"Unsupported protocol: {line[:10]}...")
    
    @classmethod
    def set_logger(cls, logger):
        """设置日志记录器"""
        cls._logger = logger
    
    @classmethod
    def get_supported_protocols(cls) -> list:
        """获取支持的协议列表"""
        return SUPPORTED_PROTOCOLS