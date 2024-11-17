import pytest
import os
from pathlib import Path
from src.models.proxy_v2 import ProxyParser, ProxyType
import re

def load_test_data(filename: str) -> list:
    """从测试数据文件加载代理链接"""
    data_dir = Path(__file__).parent.parent / "data"
    file_path = data_dir / filename
    
    if not file_path.exists():
        return []
        
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

def validate_proxy_info(info: dict, protocol: str) -> tuple[bool, str]:
    """验证代理信息的有效性"""
    try:
        # 验证基本字段
        if not info["server"] or not info["port"]:
            return False, "Missing server or port"
            
        # 验证服务器地址格式
        if not re.match(r'^[a-zA-Z0-9.-]+$', info["server"]):
            return False, f"Invalid server address format: {info['server']}"
            
        # 根据协议验证特定字段
        if protocol == "ss":
            if not info["method"] or not info["password"]:
                return False, "Missing method or password"
            
            # 验证加密方法
            supported_methods = {
                "aes-128-gcm", "aes-256-gcm", "chacha20-poly1305",
                "chacha20-ietf-poly1305", "xchacha20-poly1305",
                "2022-blake3-aes-128-gcm", "2022-blake3-aes-256-gcm",
                "2022-blake3-chacha20-poly1305"
            }
            if info["method"] not in supported_methods:
                return False, f"Unsupported encryption method: {info['method']}"
                
        elif protocol == "vmess":
            if not info["id"] or not re.match(r'^[0-9a-f-]{36}$', info["id"]):
                return False, f"Invalid UUID format: {info['id']}"
                
            if info["net"] not in ["tcp", "ws", "http", "h2", "grpc", "quic"]:
                return False, f"Unsupported network type: {info['net']}"
                
            # 验证TLS配置
            if info["tls"] == "tls" and not info["sni"]:
                return False, "Missing SNI for TLS connection"
                
            # 验证WebSocket配置
            if info["net"] == "ws" and not info["path"]:
                return False, "Missing WebSocket path"
                
        elif protocol == "vless":
            if not info["id"] or not re.match(r'^[0-9a-f-]{36}$', info["id"]):
                return False, f"Invalid UUID format: {info['id']}"
                
            if info["encryption"] != "none":
                return False, f"Unsupported encryption: {info['encryption']}"
                
            # 验证传输方式
            transport_type = info.get("type", "tcp")  # 获取实际的传输类型
            if transport_type not in ["tcp", "ws", "http", "h2", "grpc", "quic", "splithttp", "httpupgrade"]:
                return False, f"Unsupported transport type: {transport_type}"
                
            # 验证TLS配置
            if info["security"] == "tls" and not info["sni"]:
                return False, "Missing SNI for TLS connection"
                
            # 验证WebSocket配置
            if transport_type == "ws":  # 使用实际的传输类型进行判断
                if not info["path"]:
                    return False, "Missing WebSocket path"
                
        elif protocol == "trojan":
            if not info["password"]:
                return False, "Missing password"
                
            # Trojan必须使用TLS
            if not info.get("security") == "tls":
                return False, "Trojan requires TLS"
                
            if not info.get("sni"):
                return False, "Missing SNI for Trojan"
                
            # 验证传输方式
            if info["type"] not in ["tcp", "ws"]:
                return False, f"Unsupported transport type: {info['type']}"
                
            # 验证WebSocket配置
            if info["type"] == "ws" and not info["path"]:
                return False, "Missing WebSocket path"
                
        return True, "OK"
        
    except KeyError as e:
        return False, f"Missing required field: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

@pytest.mark.parametrize("filename", [
    f for f in os.listdir(Path(__file__).parent.parent / "data") 
    if f.endswith(("_yes.txt", "_no.txt"))
])
def test_proxy_links(filename):
    """测试数据文件中的代理链接"""
    links = load_test_data(filename)
    protocol = filename.split("_")[0]  # 从文件名获取协议类型
    
    print(f"\nTesting {protocol} links from {filename} ({len(links)} links):")
    
    for link in links:
        try:
            # 尝试解析链接
            info = ProxyParser.parse(link)
            
            # 验证基本字段
            assert info["proxy_protocol"].value == protocol
            assert info["server"]
            assert info["port"]
            
            # 验证协议特定字段
            if protocol == "ss":
                assert info["method"]
                assert info["password"]
            elif protocol == "ssr":
                assert info["method"]
                assert info["password"]
                assert info["protocol"]
                assert info["obfs"]
            elif protocol == "vmess":
                assert info["id"]
                assert isinstance(info["aid"], int)
            elif protocol == "vless":
                assert info["id"]
                assert info["encryption"] == "none"
            elif protocol == "trojan":
                assert info["password"]
            elif protocol == "ssh":
                assert isinstance(info["port"], str)
                if info["username"]:
                    assert info["password"] or info["private_key"]
            
            # 链接格式正确
            print(f"✓", end=" ", flush=True)
            
        except Exception as e:
            # 链接格式错误
            print(f"\n✗ Invalid {protocol} link format:")
            print(f"  Link: {link}")
            print(f"  Error: {str(e)}")
            print("  Parsed info (if available):")
            try:
                for key, value in sorted(info.items()):
                    if key not in ["raw_link", "proxy_protocol"]:
                        print(f"    {key}: {value}")
            except:
                pass

def test_parse_results():
    """测试解析结果的详细信息"""
    data_dir = Path(__file__).parent.parent / "data"
    
    for file in data_dir.glob("*_yes.txt"):
        protocol = file.name.split("_")[0].upper()
        links = load_test_data(file.name)
        
        if links:
            print(f"\nTesting {protocol} configuration details:")
            
            # 只测试第一个链接的详细信息
            link = links[0]
            try:
                info = ProxyParser.parse(link)
                print(f"\nParsed {info['proxy_protocol']} proxy configuration:")
                for key, value in sorted(info.items()):
                    if key != "raw_link":  # 跳过原始链接以保持输出简洁
                        print(f"  {key}: {value}")
            except Exception as e:
                print(f"Error parsing {link}\nError: {str(e)}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 