import re
from typing import Optional, Any, Dict
from .constants import (
    DEFAULT_VALUES,
    INVALID_CHARS,
    MAX_LENGTHS,
    PARAM_PATTERNS,
    SPECIAL_CHARS,
    CLEAN_FIELDS
)

class StringCleaner:
    """字符串清理工具"""
    
    _logger = None  # 类级别的logger
    
    @classmethod
    def set_logger(cls, logger):
        """设置日志记录器"""
        cls._logger = logger
    
    @classmethod
    def clean_value(cls, value: str, field_name: str, default: Any = None) -> str:
        """
        清理字段值中的特殊字符
        
        Args:
            value: 要清理的值
            field_name: 字段名称
            default: 默认值（如果未提供，使用DEFAULT_VALUES中的值）
            
        Returns:
            str: 清理后的值
        """
        if not isinstance(value, str):
            return value
            
        # 获取默认值
        if default is None:
            default = DEFAULT_VALUES.get(field_name, '')
            
        try:
            # 移除前后空白
            value = value.strip()
            
            # 检查长度限制
            max_length = MAX_LENGTHS.get(field_name)
            if max_length and len(value) > max_length:
                if cls._logger:
                    cls._logger.debug(f"Value too long for {field_name}: {len(value)} > {max_length}")
                return default
            
            # 检查非法字符
            invalid_chars = INVALID_CHARS.get(field_name, INVALID_CHARS['param'])
            if any(c in value for c in invalid_chars):
                if cls._logger:
                    cls._logger.debug(f"Invalid characters in {field_name}: {value}")
                return default
            
            # 检查特殊字符
            special_chars = SPECIAL_CHARS.get(field_name, [])
            if special_chars and any(c in value for c in special_chars):
                if cls._logger:
                    cls._logger.debug(f"Special characters in {field_name}: {value}")
                return default
            
            # 检查格式模式
            pattern = PARAM_PATTERNS.get(field_name)
            if pattern and not re.match(pattern, value):
                if cls._logger:
                    cls._logger.debug(f"Invalid format for {field_name}: {value}")
                return default
            
            return value
            
        except Exception as e:
            if cls._logger:
                cls._logger.error(f"Error cleaning {field_name}: {str(e)}")
            return default
    
    @classmethod
    def clean_settings(cls, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理代理设置中的所有字段
        
        Args:
            settings: 代理设置字典
            
        Returns:
            Dict[str, Any]: 清理后的设置字典
        """
        if not settings:
            return {}
            
        cleaned = {}
        for key, value in settings.items():
            # 如果是需要清理的字段
            if key in CLEAN_FIELDS:
                cleaned[key] = cls.clean_value(value, key)
            # 如果是嵌套字典
            elif isinstance(value, dict):
                cleaned[key] = cls.clean_settings(value)
            # 如果是列表
            elif isinstance(value, list):
                cleaned[key] = [
                    cls.clean_settings(item) if isinstance(item, dict)
                    else cls.clean_value(item, key)
                    for item in value
                ]
            # 其他值直接保留
            else:
                cleaned[key] = value
        
        return cleaned
    
    @classmethod
    def clean_host(cls, value: str, server: str) -> str:
        """
        清理主机名
        
        Args:
            value: 主机名
            server: 服务器地址（作为默认值）
            
        Returns:
            str: 清理后的主机名
        """
        value = value.strip()
        
        # 检查长度和非法字符
        if (len(value) > MAX_LENGTHS['host'] or 
            any(c in value for c in INVALID_CHARS['host'])):
            if cls._logger:
                cls._logger.debug(f"Invalid host value: {value}")
            return server
        
        # 检查格式
        if not re.match(PARAM_PATTERNS['host'], value):
            if cls._logger:
                cls._logger.debug(f"Invalid host format: {value}")
            return server
        
        return value or server
    
    @classmethod
    def clean_path(cls, value: str) -> str:
        """
        清理路径
        
        Args:
            value: 路径
            
        Returns:
            str: 清理后的路径
        """
        value = value.strip()
        
        # 检查长度和非法字符
        if (len(value) > MAX_LENGTHS['path'] or 
            any(c in value for c in INVALID_CHARS['path'])):
            if cls._logger:
                cls._logger.debug(f"Invalid path value: {value}")
            return '/'
        
        # 检查格式
        if not re.match(PARAM_PATTERNS['path'], value):
            if cls._logger:
                cls._logger.debug(f"Invalid path format: {value}")
            return '/'
        
        # 确保以/开头
        if not value.startswith('/'):
            value = '/' + value
        
        return value
    
    @classmethod
    def clean_uuid(cls, value: str) -> Optional[str]:
        """
        清理并验证UUID
        
        Args:
            value: UUID字符串
            
        Returns:
            Optional[str]: 有效的UUID或None
        """
        if not value:
            return None
            
        # 移除所有非字母数字和连字符字符
        value = re.sub(r'[^a-fA-F0-9-]', '', value)
        
        # 检查格式
        if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', value.lower()):
            if cls._logger:
                cls._logger.debug(f"Invalid UUID format: {value}")
            return None
            
        return value.lower()