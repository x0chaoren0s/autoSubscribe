from typing import Dict, Any, List, Optional
from enum import Enum

class GliderDecoder:
    """将代理元信息解码为Glider链接格式"""
    
    @staticmethod
    def decode(proxy_info: Dict[str, Any]) -> str:
        """将代理信息解码为Glider链接格式
        格式: [安全层,][传输层,][裸协议]
        
        安全层: tls://host:port?skipVerify=true&serverName=sni
        传输层: ws://@/path?host=xxx
        裸协议: ss://method:pass@host:port
        """
        if not proxy_info or "proxy_protocol" not in proxy_info:
            raise ValueError("Invalid proxy info")
            
        protocol = proxy_info["proxy_protocol"]
        if hasattr(protocol, "value"):
            protocol = protocol.value
            
        decoder_map = {
            "ss": GliderDecoder._decode_ss,
            "ssr": GliderDecoder._decode_ssr,
            "vmess": GliderDecoder._decode_vmess,
            "vless": GliderDecoder._decode_vless,
            "trojan": GliderDecoder._decode_trojan,
            "ssh": GliderDecoder._decode_ssh,
        }
        
        decoder = decoder_map.get(protocol)
        if not decoder:
            raise ValueError(f"Unsupported protocol: {protocol}")
            
        try:
            return decoder(proxy_info)
        except Exception as e:
            raise ValueError(f"Failed to decode {protocol} link: {str(e)}")
    
    @staticmethod
    def _decode_security_layer(info: Dict[str, Any]) -> Optional[str]:
        """解码安全层配置"""
        if info.get("security") == "tls":
            params = []
            if info.get("allowInsecure", "0") == "1" or info.get("skipVerify", False):
                params.append("skipVerify=true")
            if info.get("sni"):
                params.append(f"serverName={info['sni']}")
            alpn_list = info.get("alpn", [])
            if isinstance(alpn_list, str):
                alpn_list = [a.strip() for a in alpn_list.split(",") if a.strip()]
            for alpn in alpn_list:
                params.append(f"alpn={alpn}")
            
            base = f"tls://{info['server']}:{info['port']}"
            return f"{base}?{'&'.join(params)}" if params else base
        return None
    
    @staticmethod
    def _decode_transport_layer(info: Dict[str, Any]) -> Optional[str]:
        """解码传输层配置"""
        transport_type = info.get("type", info.get("net", "tcp"))
        if transport_type == "ws":
            path = info.get("path", "")
            if "," in path:
                return None
                
            params = []
            if path:
                params.append(f"path={path}")
            if info.get("host"):
                params.append(f"host={info['host']}")
            
            return f"ws://@{'?' + '&'.join(params) if params else ''}"
        return None
    
    @staticmethod
    def _decode_ss(info: Dict[str, Any]) -> str:
        """解码为Shadowsocks的Glider链接格式"""
        return f"ss://{info['method']}:{info['password']}@{info['server']}:{info['port']}"
    
    @staticmethod
    def _decode_ssr(info: Dict[str, Any]) -> str:
        """解码为ShadowsocksR的Glider链接格式"""
        base = f"ssr://{info['method']}:{info['password']}@{info['server']}:{info['port']}"
        params = []
        
        if info.get("protocol"):
            params.append(f"protocol={info['protocol']}")
        if info.get("protocol_param"):
            params.append(f"protocol_param={info['protocol_param']}")
        if info.get("obfs"):
            params.append(f"obfs={info['obfs']}")
        if info.get("obfs_param"):
            params.append(f"obfs_param={info['obfs_param']}")
            
        return f"{base}?{'&'.join(params)}" if params else base
    
    @staticmethod
    def _decode_vmess(info: Dict[str, Any]) -> str:
        """解码为VMess的Glider链接格式"""
        parts = []
        
        # 1. 安全层
        security_layer = GliderDecoder._decode_security_layer(info)
        if security_layer:
            parts.append(security_layer)
            
        # 2. 传输层
        transport_layer = GliderDecoder._decode_transport_layer(info)
        if transport_layer:
            parts.append(transport_layer)
            
        # 3. 裸协议
        encryption = info.get("encryption", "auto")
        if encryption == "auto":
            encryption = "aes-128-gcm"
        base = f"vmess://{encryption}:{info['id']}@{info['server']}:{info['port']}"
        if "aid" in info:
            base = f"{base}?alterID={info['aid']}"
        parts.append(base)
        
        return ",".join(parts)
    
    @staticmethod
    def _decode_vless(info: Dict[str, Any]) -> str:
        """解码为VLESS的Glider链接格式"""
        parts = []
        
        # 1. 安全层
        security_layer = GliderDecoder._decode_security_layer(info)
        if security_layer:
            parts.append(security_layer)
            
        # 2. 传输层
        transport_layer = GliderDecoder._decode_transport_layer(info)
        if transport_layer:
            parts.append(transport_layer)
            
        # 3. 裸协议
        base = f"vless://{info['id']}@{info['server']}:{info['port']}"
        if info.get("fallback"):
            base = f"{base}?fallback={info['fallback']}"
        parts.append(base)
        
        return ",".join(parts)
    
    @staticmethod
    def _decode_trojan(info: Dict[str, Any]) -> str:
        """解码为Trojan的Glider链接格式"""
        parts = []
        
        # 1. 安全层
        security_layer = GliderDecoder._decode_security_layer(info)
        if security_layer:
            parts.append(security_layer)
            
        # 2. 传输层
        transport_layer = GliderDecoder._decode_transport_layer(info)
        if transport_layer:
            parts.append(transport_layer)
            
        # 3. 裸协议
        base = f"trojan://{info['password']}@{info['server']}:{info['port']}"
        parts.append(base)
        
        return ",".join(parts)
    
    @staticmethod
    def _decode_ssh(info: Dict[str, Any]) -> str:
        """解码为SSH的Glider链接格式"""
        # SSH不需要多层配置
        if info.get("username"):
            if info.get("password"):
                auth = f"{info['username']}:{info['password']}"
            else:
                auth = info['username']
            base = f"ssh://{auth}@{info['server']}:{info['port']}"
        else:
            base = f"ssh://{info['server']}:{info['port']}"
            
        params = []
        if info.get("private_key"):
            params.append(f"key={info['private_key']}")
        if info.get("timeout"):
            params.append(f"timeout={info['timeout']}")
            
        return f"{base}?{'&'.join(params)}" if params else base 