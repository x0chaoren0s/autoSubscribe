from dataclasses import dataclass
from typing import Optional

@dataclass
class Proxy:
    """代理配置模型类"""
    raw_link: str          # 原始代理链接
    proxy_type: str        # 代理类型：'ss', 'vmess', 'vless', 'trojan', 'ssh'
    server: str           # 服务器地址
    port: int            # 端口号
    settings: dict       # 存储协议特定的配置