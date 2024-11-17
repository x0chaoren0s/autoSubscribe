from enum import Enum
import base64
import json
import urllib.parse
from typing import Dict, Any

class ProxyProtocol(str, Enum):
    """代理协议类型"""
    SS = "ss"
    SSR = "ssr"
    VMESS = "vmess"
    VLESS = "vless"
    TROJAN = "trojan"
    SSH = "ssh"

class ProxyEncoder:
    """代理链接编码器 - 将代理链接编码为标准格式的元信息字典"""
    
    @staticmethod
    def encode(raw_link: str) -> Dict[str, Any]:
        """将代理链接编码为元信息字典"""
        if not raw_link or not isinstance(raw_link, str):
            raise ValueError("Invalid proxy link")
            
        # 移除空白字符
        raw_link = raw_link.strip()
        
        # 获取代理类型
        protocol = ProxyEncoder._get_protocol(raw_link)
        if not protocol:
            raise ValueError(f"Unsupported protocol: {raw_link}")
            
        # 根据类型编码
        encoder_map = {
            ProxyProtocol.SS: ProxyEncoder._encode_ss,
            ProxyProtocol.SSR: ProxyEncoder._encode_ssr,
            ProxyProtocol.VMESS: ProxyEncoder._encode_vmess,
            ProxyProtocol.VLESS: ProxyEncoder._encode_vless,
            ProxyProtocol.TROJAN: ProxyEncoder._encode_trojan,
            ProxyProtocol.SSH: ProxyEncoder._encode_ssh
        }
        
        encoder = encoder_map.get(protocol)
        if not encoder:
            raise ValueError(f"No encoder found for protocol: {protocol}")
            
        try:
            proxy_info = encoder(raw_link)
            # 添加通用字段
            proxy_info.update({
                "proxy_protocol": protocol,
                "raw_link": raw_link,
                "name": proxy_info.get("name", ""),
                "server": proxy_info.get("server", ""),
                "port": proxy_info.get("port", "22") if protocol == ProxyProtocol.SSH else proxy_info.get("port", 0)
            })
            return proxy_info
        except Exception as e:
            raise ValueError(f"Failed to encode {protocol} link: {str(e)}")

    @staticmethod
    def _get_protocol(raw_link: str) -> ProxyProtocol:
        """获取代理协议类型"""
        if raw_link.startswith("ss://"):
            return ProxyProtocol.SS
        elif raw_link.startswith("ssr://"):
            return ProxyProtocol.SSR
        elif raw_link.startswith("vmess://"):
            return ProxyProtocol.VMESS
        elif raw_link.startswith("vless://"):
            return ProxyProtocol.VLESS
        elif raw_link.startswith("trojan://"):
            return ProxyProtocol.TROJAN
        elif raw_link.startswith("ssh://"):
            return ProxyProtocol.SSH
        return None

    # ... (其余编码方法保持不变，只需将方法名从_parse_xxx改为_encode_xxx) 
    @staticmethod
    def _encode_ss(raw_link: str) -> Dict[str, Any]:
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
            "port": int(port),  # 转换为���数
            "method": method,
            "password": password,
            # 默认值
            "udp": True,
            "plugin": "",
            "plugin_opts": ""
        }

    @staticmethod
    def _encode_ssr(raw_link: str) -> Dict[str, Any]:
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
    def _encode_vmess(raw_link: str) -> Dict[str, Any]:
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
    def _encode_vless(raw_link: str) -> Dict[str, Any]:
        """编码 VLESS 链接"""
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
            
        # 处理alpn参数，可能是逗号分隔的字符串
        alpn = params.get("alpn", "")
        if alpn:
            alpn = [a.strip() for a in alpn.split(",") if a.strip()]
        
        return {
            "name": name,
            "server": server,
            "port": int(port),
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
            "alpn": alpn,  # 保存为列表
            # 默认值
            "publicKey": params.get("pbk", ""),
            "shortId": params.get("sid", ""),
            "spiderX": params.get("spx", "")
        }

    @staticmethod
    def _encode_trojan(raw_link: str) -> Dict[str, Any]:
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
    def _encode_ssh(raw_link: str) -> Dict[str, Any]:
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