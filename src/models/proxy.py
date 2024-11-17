import re
import json
import base64
import urllib.parse
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class ProxyType(str, Enum):
    SS = "ss"
    SSR = "ssr" 
    VMESS = "vmess"
    VLESS = "vless"
    TROJAN = "trojan"
    SSH = "ssh"

class ProxyParser:
    """代理链接解析器"""
    
    @staticmethod
    def parse(raw_link: str) -> Dict[str, Any]:
        """解析代理链接,返回代理配置字典"""
        if not raw_link or not isinstance(raw_link, str):
            raise ValueError("Invalid proxy link")
            
        # 移除空白字符
        raw_link = raw_link.strip()
        
        # 获取代理类型
        proxy_type = ProxyParser._get_proxy_type(raw_link)
        if not proxy_type:
            raise ValueError(f"Unsupported proxy type: {raw_link}")
            
        # 根据类型解析
        parser_map = {
            ProxyType.SS: ProxyParser._parse_ss,
            ProxyType.SSR: ProxyParser._parse_ssr,
            ProxyType.VMESS: ProxyParser._parse_vmess,
            ProxyType.VLESS: ProxyParser._parse_vless,
            ProxyType.TROJAN: ProxyParser._parse_trojan,
            ProxyType.SSH: ProxyParser._parse_ssh
        }
        
        parser = parser_map.get(proxy_type)
        if not parser:
            raise ValueError(f"No parser found for type: {proxy_type}")
            
        try:
            proxy_info = parser(raw_link)
            # 添加通用字段，使用proxy_protocol来存储代理类型
            proxy_info.update({
                "proxy_protocol": proxy_type,  # 改用proxy_protocol存储代理协议类型
                "raw_link": raw_link,
                "name": proxy_info.get("name", ""),
                "server": proxy_info.get("server", ""),
                # 端口处理：SSH保持字符串，其他转为整数
                "port": proxy_info.get("port", "22") if proxy_type == ProxyType.SSH else proxy_info.get("port", 0)
            })
            return proxy_info
        except Exception as e:
            raise ValueError(f"Failed to parse {proxy_type} link: {str(e)}")

    @staticmethod
    def _get_proxy_type(raw_link: str) -> Optional[ProxyType]:
        """获取代理类型"""
        if raw_link.startswith("ss://"):
            return ProxyType.SS
        elif raw_link.startswith("ssr://"):
            return ProxyType.SSR
        elif raw_link.startswith("vmess://"):
            return ProxyType.VMESS
        elif raw_link.startswith("vless://"):
            return ProxyType.VLESS
        elif raw_link.startswith("trojan://"):
            return ProxyType.TROJAN
        elif raw_link.startswith("ssh://"):
            return ProxyType.SSH
        return None

    @staticmethod
    def _parse_ss(raw_link: str) -> Dict[str, Any]:
        """解析 Shadowsocks 链接"""
        # 移除前缀
        content = raw_link[5:]
        
        # 处理 SIP002 格式
        if "@" in content:
            # 示例: ss://YWVzLTEyOC1nY206dGVzdA@192.168.100.1:8888#Example
            if "#" in content:
                content, name = content.split("#", 1)
            else:
                name = ""
                
            user_info, server_info = content.split("@", 1)
            
            # 解码用户信息
            try:
                user_info = base64.urlsafe_b64decode(user_info + "=" * (-len(user_info) % 4)).decode()
            except:
                # 可能已经是解码后的格式
                pass
                
            method, password = user_info.split(":", 1)
            
            # 处理服务器信息，考虑可能存在的插件参数
            if "/?" in server_info:
                server_port, plugin_info = server_info.split("/?", 1)
            else:
                server_port = server_info
                plugin_info = ""
                
            server, port = server_port.split(":", 1)
            
            # 如果端口后还有其他内容，只取端口部分
            port = port.split("/")[0]
            
        # 处理传统格式
        else:
            # 示例: ss://YWVzLTEyOC1nY206dGVzdEAxOTIuMTY4LjEwMC4xOjg4ODg#Example
            if "#" in content:
                content, name = content.split("#", 1)
            else:
                name = ""
                
            try:
                content = base64.urlsafe_b64decode(content + "=" * (-len(content) % 4)).decode()
            except:
                raise ValueError("Invalid base64 encoding")
                
            method, rest = content.split(":", 1)
            password, server_info = rest.split("@", 1)
            server, port = server_info.split(":", 1)
            
        return {
            "name": urllib.parse.unquote(name),
            "server": server,
            "port": int(port),  # 转换为整数
            "method": method,
            "password": password,
            # 默认值
            "udp": True,
            "plugin": "",
            "plugin_opts": ""
        }

    @staticmethod
    def _parse_ssr(raw_link: str) -> Dict[str, Any]:
        """解析 ShadowsocksR 链接"""
        # 移除前缀
        content = raw_link[6:]
        
        try:
            content = base64.urlsafe_b64decode(content + "=" * (-len(content) % 4)).decode()
        except:
            raise ValueError("Invalid base64 encoding")
            
        # 解析主要部分和参数部分
        if "?" in content:
            main_part, params_str = content.split("?", 1)
        else:
            main_part, params_str = content, ""
            
        # 解析主要部分
        parts = main_part.split(":", 5)
        if len(parts) != 6:
            raise ValueError("Invalid SSR link format")
            
        server, port, protocol, method, obfs, password_b64 = parts
        
        try:
            # 修改这里：移除密码中的填充字符
            password = base64.urlsafe_b64decode(password_b64 + "=" * (-len(password_b64) % 4)).decode().rstrip('\x0f')
        except:
            raise ValueError("Invalid password encoding")
            
        # 解析参数
        params = {}
        if params_str:
            for item in params_str.split("&"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    try:
                        params[k] = base64.urlsafe_b64decode(v + "=" * (-len(v) % 4)).decode()
                    except:
                        params[k] = v
                        
        return {
            "name": params.get("remarks", ""),
            "server": server,
            "port": int(port),  # 转换为整数
            "method": method,
            "password": password,
            "protocol": protocol,
            "protocol_param": params.get("protoparam", ""),
            "obfs": obfs,
            "obfs_param": params.get("obfsparam", ""),
            # 默认值
            "udp": True
        }

    @staticmethod
    def _parse_vmess(raw_link: str) -> Dict[str, Any]:
        """解析 VMess 链接"""
        # 移除前缀
        content = raw_link[8:]
        
        try:
            content = base64.urlsafe_b64decode(content + "=" * (-len(content) % 4)).decode()
            config = json.loads(content)
        except:
            raise ValueError("Invalid VMess link format")
            
        # 提取信息并确保aid是整数
        return {
            "name": config.get("ps", ""),
            "server": config.get("add", ""),
            "port": int(config.get("port", 0)),  # 转换为整数
            "id": config.get("id", ""),
            "aid": int(config.get("aid", 0)),
            "type": config.get("net", "tcp"),  # 使用net字段作为传输类型
            "host": config.get("host", ""),
            "path": config.get("path", ""),
            "security": "tls" if config.get("tls") == "tls" else "",
            "sni": config.get("sni", ""),
            "encryption": config.get("scy", "auto"),
            "flow": config.get("flow", ""),
            "alpn": config.get("alpn", []),
            "fingerprint": config.get("fp", ""),
            "publicKey": config.get("pbk", ""),
            "shortId": config.get("sid", ""),
            "spiderX": config.get("spx", "")
        }

    @staticmethod
    def _parse_vless(raw_link: str) -> Dict[str, Any]:
        """解析 VLESS 链接"""
        # 移除前缀
        content = raw_link[8:]
        
        # 分离名称
        if "#" in content:
            content, name = content.split("#", 1)
            name = urllib.parse.unquote(name)
        else:
            name = ""
            
        # 分离用户信息和服务器信息
        if "@" not in content:
            raise ValueError("Invalid VLESS link format")
            
        user_info, server_info = content.split("@", 1)
        
        # 分离服务器和端口
        if ":" not in server_info:
            raise ValueError("Invalid server address format")
            
        server, port = server_info.split(":", 1)
        if "?" in port:
            port, params_str = port.split("?", 1)
        else:
            params_str = ""
            
        # 解析参数
        params = {}
        if params_str:
            params = dict(urllib.parse.parse_qsl(params_str))
            
        return {
            "name": name,
            "server": server,
            "port": int(port),  # 转换为整数
            "id": user_info,
            "flow": params.get("flow", ""),
            "encryption": params.get("encryption", "none"),
            "security": params.get("security", ""),
            "sni": params.get("sni", ""),
            "fp": params.get("fp", ""),
            "type": params.get("type", "tcp"),
            "host": params.get("host", ""),
            "path": params.get("path", ""),
            "headerType": params.get("headerType", ""),
            # 添加fallback参数
            "fallback": params.get("fallback", ""),
            # 默认值
            "alpn": params.get("alpn", "").split(",") if params.get("alpn") else [],
            "publicKey": params.get("pbk", ""),
            "shortId": params.get("sid", ""),
            "spiderX": params.get("spx", "")
        }

    @staticmethod
    def _parse_trojan(raw_link: str) -> Dict[str, Any]:
        """解析 Trojan 链接"""
        # 移除前缀
        content = raw_link[9:]
        
        # 分离名称
        if "#" in content:
            content, name = content.split("#", 1)
            name = urllib.parse.unquote(name)
        else:
            name = ""
            
        # 分离密码和服务器信息
        if "@" not in content:
            raise ValueError("Invalid Trojan link format")
            
        password, server_info = content.split("@", 1)
        
        # 分离服务器和端口
        if ":" not in server_info:
            raise ValueError("Invalid server address format")
            
        server, port = server_info.split(":", 1)
        if "?" in port:
            port, params_str = port.split("?", 1)
        else:
            params_str = ""
            
        # 解析参数
        params = {}
        if params_str:
            params = dict(urllib.parse.parse_qsl(params_str))
            
        return {
            "name": name,
            "server": server,
            "port": int(port),  # 转换为整数
            "password": password,
            # 修改这里：只在明确指定时才设置TLS
            "security": params.get("security", ""),  # 不再默认为tls
            "sni": params.get("sni", ""),
            "type": params.get("type", "tcp"),
            "host": params.get("host", ""),
            "path": params.get("path", ""),
            # 添加allowInsecure参数
            "allowInsecure": params.get("allowInsecure", "0"),
            # 默认值
            "alpn": params.get("alpn", "").split(",") if params.get("alpn") else [],
            "fingerprint": params.get("fp", ""),
            "skipVerify": params.get("allowInsecure", "0") == "1",
            "udp": True
        }

    @staticmethod
    def _parse_ssh(raw_link: str) -> Dict[str, Any]:
        """解析 SSH 链接"""
        # 移除前缀
        content = raw_link[6:]
        
        # 分离服务器信息和参数
        if "?" in content:
            server_info, params_str = content.split("?", 1)
        else:
            server_info, params_str = content, ""
            
        # 解析用户名、密码和服务器信息
        if "@" in server_info:
            auth_info, host_info = server_info.split("@", 1)
            if ":" in auth_info:
                username, password = auth_info.split(":", 1)
            else:
                username, password = auth_info, ""
        else:
            username, password = "", ""
            host_info = server_info
            
        # 解析服务器和端口
        if ":" in host_info:
            server, port = host_info.split(":", 1)
        else:
            server, port = host_info, "22"
            
        # 解析参数
        params = {}
        if params_str:
            params = dict(urllib.parse.parse_qsl(params_str))
            
        return {
            "name": params.get("name", ""),
            "server": server,
            "port": port,  # 保持端口为字符串，因为测试期望它是字符串
            "username": username,
            "password": password,
            "private_key": params.get("key", ""),
            "key_password": params.get("key_password", ""),
            "ssh_options": {k[4:]: v for k, v in params.items() if k.startswith("ssh_")}
        } 