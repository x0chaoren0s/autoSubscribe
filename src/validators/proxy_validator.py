from typing import Dict, Any, Tuple
import re
import yaml

class ProxyValidator:
    """代理配置验证器"""
    
    def __init__(self, config_path: str = 'config/proxies_filter.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
    def validate(self, proxy_info: Dict[str, Any]) -> Tuple[bool, str]:
        """验证代理配置的有效性"""
        try:
            # 获取协议类型
            protocol = proxy_info["proxy_protocol"].value
            
            # 验证基本字段
            if not proxy_info.get("server") or not proxy_info.get("port"):
                return False, "Missing server or port"
                
            # 验证服务器地址格式
            if not re.match(r'^[a-zA-Z0-9.-]+$', proxy_info["server"]):
                return False, f"Invalid server address format: {proxy_info['server']}"
                
            # 根据协议验证
            validator_map = {
                "ss": self._validate_ss,
                "ssr": self._validate_ssr,
                "vmess": self._validate_vmess,
                "vless": self._validate_vless,
                "trojan": self._validate_trojan,
                "ssh": self._validate_ssh
            }
            
            validator = validator_map.get(protocol)
            if not validator:
                return False, f"Unsupported protocol: {protocol}"
                
            return validator(proxy_info)
            
        except KeyError as e:
            return False, f"Missing required field: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
            
    def _validate_ss(self, info: Dict[str, Any]) -> Tuple[bool, str]:
        """验证Shadowsocks配置"""
        if not info.get("method") or not info.get("password"):
            return False, "Missing method or password"
            
        # 验证加密方法
        supported_methods = set(self.config["protocols"]["ss"]["methods"])
        if info["method"] not in supported_methods:
            return False, f"Unsupported encryption method: {info['method']}"
            
        return True, "OK"
        
    def _validate_vmess(self, info: Dict[str, Any]) -> Tuple[bool, str]:
        """验证VMess配置"""
        if not info.get("id") or not re.match(r'^[0-9a-f-]{36}$', info["id"]):
            return False, f"Invalid UUID format: {info['id']}"
            
        # 验证传输协议
        transport_type = info.get("type", "tcp")
        supported_transports = set(self.config["protocols"]["vmess"]["transports"])
        if transport_type not in supported_transports:
            return False, f"Unsupported transport type: {transport_type}"
            
        # 验证加密方法
        security = info.get("encryption", "auto")
        if security != "auto":
            supported_securities = set(self.config["protocols"]["vmess"]["securities"])
            if security not in supported_securities:
                return False, f"Unsupported security type: {security}"
                
        # 验证WebSocket配置
        if transport_type == "ws":
            if not info.get("path"):
                return False, "Missing WebSocket path"
            if "," in info["path"]:
                return False, "Invalid character ',' in WebSocket path"
                
        return True, "OK"
        
    def _validate_vless(self, info: Dict[str, Any]) -> Tuple[bool, str]:
        """验证VLESS配置"""
        if not info.get("id") or not re.match(r'^[0-9a-f-]{36}$', info["id"]):
            return False, f"Invalid UUID format: {info['id']}"
            
        # 验证传输协议
        transport_type = info.get("type", "tcp")
        supported_transports = set(self.config["protocols"]["vless"]["transports"])
        if transport_type not in supported_transports:
            return False, f"Unsupported transport type: {transport_type}"
            
        # 验证WebSocket配置
        if transport_type == "ws":
            if not info.get("path"):
                return False, "Missing WebSocket path"
            if "," in info["path"]:
                return False, "Invalid character ',' in WebSocket path"
                
        return True, "OK"
        
    def _validate_trojan(self, info: Dict[str, Any]) -> Tuple[bool, str]:
        """验证Trojan配置"""
        if not info.get("password"):
            return False, "Missing password"
            
        # 验证传输协议
        transport_type = info.get("type", "tcp")
        supported_transports = set(self.config["protocols"]["trojan"]["transports"])
        if transport_type not in supported_transports:
            return False, f"Unsupported transport type: {transport_type}"
            
        # 验证WebSocket配置
        if transport_type == "ws":
            if not info.get("path"):
                return False, "Missing WebSocket path"
            if "," in info["path"]:
                return False, "Invalid character ',' in WebSocket path"
                
        return True, "OK"
        
    def _validate_ssh(self, info: Dict[str, Any]) -> Tuple[bool, str]:
        """验证SSH配置"""
        if info.get("username") and not (info.get("password") or info.get("private_key")):
            return False, "Missing password or private key"
            
        return True, "OK"
        
    def _validate_ssr(self, info: Dict[str, Any]) -> Tuple[bool, str]:
        """验证ShadowsocksR配置"""
        if not info.get("method") or not info.get("password"):
            return False, "Missing method or password"
            
        if not info.get("protocol"):
            return False, "Missing protocol"
            
        if not info.get("obfs"):
            return False, "Missing obfs"
            
        return True, "OK" 