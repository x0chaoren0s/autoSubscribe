# 导入所有协议解析器以确保装饰器被执行
from .vmess_parser import VmessParser
from .vless_parser import VlessParser
from .ss_parser import SSParser
from .trojan_parser import TrojanParser
from .ssh_parser import SSHParser

# 导出所有解析器类
__all__ = ['VmessParser', 'VlessParser', 'SSParser', 'TrojanParser', 'SSHParser'] 