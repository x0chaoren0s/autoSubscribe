from typing import Dict, Type
from .base_protocol_parser import BaseProtocolParser

class ProtocolParserFactory:
    """协议解析器工厂"""
    
    _parsers: Dict[str, Type[BaseProtocolParser]] = {}
    _logger = None
    
    @classmethod
    def register(cls, parser_class: Type[BaseProtocolParser]):
        """注册装饰器"""
        cls._parsers[parser_class.protocol_prefix()] = parser_class
        return parser_class
    
    @classmethod
    def set_logger(cls, logger):
        """设置日志记录器"""
        cls._logger = logger
    
    @classmethod
    def create_parser(cls, line: str) -> BaseProtocolParser:
        """创建合适的协议解析器"""
        for prefix, parser_class in cls._parsers.items():
            if line.startswith(prefix):
                return parser_class(logger=cls._logger)
        raise ValueError(f"Unsupported protocol: {line[:10]}...") 