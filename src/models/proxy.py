from typing import Dict, Optional
from ..utils.constants import (
    SUPPORTED_PROTOCOLS,
    SUPPORTED_SS_METHODS,
    LEGACY_SS_METHODS,
    DEFAULT_PORTS,
    DEFAULT_VALUES,
    GLIDER_STRATEGIES,
    VMESS_METHODS,
    VMESS_NETWORKS,
    TLS_SETTINGS,
    WS_SETTINGS
)
from ..utils.string_cleaner import StringCleaner

class Proxy:
    """代理模型"""
    
    def __init__(self, raw_link: str, proxy_type: str, server: str, port: int, settings: Dict):
        """
        初始化代理对象
        
        Args:
            raw_link: 原始代理链接
            proxy_type: 代理类型 (ss/vmess/vless/trojan/ssh)
            server: 服务器地址
            port: 端口号
            settings: 代理设置
        """
        if proxy_type not in SUPPORTED_PROTOCOLS:
            raise ValueError(f"Unsupported protocol: {proxy_type}")
            
        self.raw_link = raw_link
        self.proxy_type = proxy_type
        self.server = server
        self.port = port or DEFAULT_PORTS.get(proxy_type, 443)
        self.settings = settings
        
        # 验证SS加密方法
        if proxy_type == 'ss':
            method = settings.get('method', '').lower()
            if not method:
                raise ValueError("Missing encryption method for SS proxy")
            if method not in SUPPORTED_SS_METHODS and method not in LEGACY_SS_METHODS:
                raise ValueError(f"Unknown encryption method: {method}")
    
    def __str__(self) -> str:
        """返回代理的字符串表示"""
        return f"{self.proxy_type.upper()}://{self.server}:{self.port}"
    
    def __repr__(self) -> str:
        """返回代理的详细表示"""
        settings_str = ', '.join(
            f"{k}={v}" for k, v in self.settings.items() 
            if k not in ['password', 'id', 'uuid'] and v
        )
        return f"Proxy({self.proxy_type}, {self.server}:{self.port}, {settings_str})"
    
    def __eq__(self, other) -> bool:
        """判断两个代理是否相等"""
        if not isinstance(other, Proxy):
            return False
        return self.raw_link == other.raw_link
    
    def __hash__(self) -> int:
        """返回代理的哈希值"""
        return hash(self.raw_link)
    
    def get_tag(self) -> str:
        """返回代理的标签"""
        if self.proxy_type == 'ss':
            method = self.settings.get('method', '')
            return f"SS-{method}-{self.server}:{self.port}"
        elif self.proxy_type == 'vmess':
            return f"VMess-{self.server}:{self.port}"
        elif self.proxy_type == 'vless':
            flow = self.settings.get('flow', '')
            flow_tag = f"-{flow}" if flow else ""
            return f"VLESS{flow_tag}-{self.server}:{self.port}"
        elif self.proxy_type == 'trojan':
            return f"Trojan-{self.server}:{self.port}"
        elif self.proxy_type == 'ssh':
            user = self.settings.get('username', '')
            return f"SSH-{user}@{self.server}:{self.port}"
        return f"{self.proxy_type.upper()}-{self.server}:{self.port}"
    
    def is_valid(self) -> bool:
        """检查代理配置是否有效"""
        try:
            if not self.server or not self.port:
                return False
                
            if self.proxy_type == 'ss':
                return bool(
                    self.settings.get('method') and 
                    self.settings.get('password')
                )
            elif self.proxy_type == 'vmess':
                return bool(self.settings.get('id'))
            elif self.proxy_type == 'vless':
                return bool(self.settings.get('uuid'))
            elif self.proxy_type == 'trojan':
                return bool(self.settings.get('password'))
            elif self.proxy_type == 'ssh':
                return bool(
                    self.settings.get('username') and 
                    (self.settings.get('password') or self.settings.get('private_key'))
                )
            return False
            
        except Exception:
            return False
    
    def get_security_info(self) -> Optional[str]:
        """获取安全传输信息"""
        security = self.settings.get('security', 'none')
        if security == 'tls':
            return f"TLS({self.settings.get('sni', '')})"
        elif security == 'reality':
            return f"Reality({self.settings.get('sni', '')})"
        return None
    
    def clean_settings(self) -> None:
        """清理代理设置中的特殊字符"""
        cleaned_settings = {}
        for key, value in self.settings.items():
            if isinstance(value, str):
                cleaned_settings[key] = StringCleaner.clean_value(value, key)
            else:
                cleaned_settings[key] = value
        self.settings = cleaned_settings
    
    def to_glider_url(self) -> Optional[str]:
        """转换为Glider URL格式"""
        try:
            if self.proxy_type == 'ss':
                method = self.settings['method'].lower()
                if method not in SUPPORTED_SS_METHODS:
                    if method in LEGACY_SS_METHODS:
                        return None  # 不支持旧的加密方法
                    # 尝试使用原始方法名
                    return f"ss://{method}:{self.settings['password']}@{self.server}:{self.port}"
                return f"ss://{SUPPORTED_SS_METHODS[method]}:{self.settings['password']}@{self.server}:{self.port}"
                
            elif self.proxy_type == 'vmess':
                # 获取加密方式
                security = self.settings.get('security', 'auto')
                if security not in VMESS_METHODS:
                    security = 'auto'
                security = VMESS_METHODS[security]
                
                # 构建基本URL
                base_url = f"vmess://{security}:{self.settings['id']}@{self.server}:{self.port}"
                
                # 添加alterID参数（如果不为0）
                aid = self.settings.get('aid', '0')
                if aid and aid != '0':
                    base_url = f"{base_url}?alterID={aid}"
                
                # 获取传输协议
                net = self.settings.get('type', 'tcp')
                if net not in VMESS_NETWORKS:
                    net = 'tcp'
                net = VMESS_NETWORKS[net]
                
                # WebSocket设置
                if net == 'ws':
                    # 构建WebSocket URL
                    ws_url = f"ws://{self.server}:{self.port}"
                    ws_params = []
                    
                    path = self.settings.get('path', '')
                    if path:
                        if path.startswith('/'):
                            path = path[1:]
                        ws_params.append(f"path={path}")
                        
                    host = self.settings.get('host', '')
                    if host:
                        ws_params.append(f"host={host}")
                    
                    if ws_params:
                        ws_url += "?" + "&".join(ws_params)
                    
                    # TLS设置
                    if self.settings.get('tls') == 'tls':
                        tls_url = f"tls://{self.server}:{self.port}"
                        tls_params = []
                        if self.settings.get('sni'):
                            tls_params.append(f"serverName={self.settings['sni']}")
                        if self.settings.get('allowInsecure', '1') == '1':
                            tls_params.append("skipVerify=true")
                        if self.settings.get('alpn'):
                            alpns = self.settings['alpn'].split(',')
                            for alpn in alpns:
                                alpn = alpn.strip()
                                if alpn:
                                    tls_params.append(f"alpn={alpn}")
                        if tls_params:
                            tls_url += "?" + "&".join(tls_params)
                        return f"{tls_url},{ws_url},{base_url}"
                    else:
                        return f"{ws_url},{base_url}"
                
                # 其他传输协议
                else:
                    # TLS设置
                    if self.settings.get('tls') == 'tls':
                        tls_url = f"tls://{self.server}:{self.port}"
                        tls_params = []
                        if self.settings.get('sni'):
                            tls_params.append(f"serverName={self.settings['sni']}")
                        if self.settings.get('allowInsecure', '1') == '1':
                            tls_params.append("skipVerify=true")
                        if self.settings.get('alpn'):
                            alpns = self.settings['alpn'].split(',')
                            for alpn in alpns:
                                alpn = alpn.strip()
                                if alpn:
                                    tls_params.append(f"alpn={alpn}")
                        if tls_params:
                            tls_url += "?" + "&".join(tls_params)
                        return f"{tls_url},{base_url}"
                    
                    return base_url
                
            elif self.proxy_type == 'trojan':
                # 检查是否使用TLS
                if self.settings.get('security') == 'tls' or self.settings.get('tls') == 'tls':
                    # 使用tls+trojanc的组合
                    tls_params = []
                    if self.settings.get('sni'):
                        tls_params.append(f"serverName={self.settings['sni']}")
                    if self.settings.get('allowInsecure', '1') == '1':
                        tls_params.append("skipVerify=true")
                    
                    # 处理alpn参数
                    if self.settings.get('alpn'):
                        alpns = self.settings['alpn'].split(',')
                        # 为每个alpn值添加单独的参数
                        for alpn in alpns:
                            alpn = alpn.strip()
                            if alpn:  # 确保不是空字符串
                                tls_params.append(f"alpn={alpn}")
                    
                    tls_url = f"tls://{self.server}:{self.port}"
                    if tls_params:
                        tls_url += "?" + "&".join(tls_params)
                    
                    trojan_url = f"trojanc://{self.settings['password']}@{self.server}:{self.port}"
                    return f"{tls_url},{trojan_url}"
                else:
                    # 不使用TLS的情况
                    return f"trojanc://{self.settings['password']}@{self.server}:{self.port}"
                
            elif self.proxy_type == 'vless':
                # VLESS现在支持了
                return f"vless://{self.settings['uuid']}@{self.server}:{self.port}"
                
            elif self.proxy_type == 'ssh':
                # SSH配置保持不变
                url = f"ssh://{self.settings['username']}"
                if self.settings.get('password'):
                    url += f":{self.settings['password']}"
                url += f"@{self.server}:{self.port}"
                
                params = []
                if self.settings.get('private_key'):
                    params.append(f"key={self.settings['private_key']}")
                if self.settings.get('private_key_password'):
                    params.append(f"key_password={self.settings['private_key_password']}")
                for key, value in self.settings.get('options', {}).items():
                    params.append(f"ssh_{key}={value}")
                
                if params:
                    url += "?" + "&".join(params)
                return url
            
            return None
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Failed to generate glider URL: {str(e)}")
            return None