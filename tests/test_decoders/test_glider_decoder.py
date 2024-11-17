import pytest
from pathlib import Path
from src.models.proxy_v2 import ProxyParser, ProxyType
from src.decoders.glider_decoder import GliderDecoder

def test_decode_ss():
    # 测试基本SS链接
    raw_link = "ss://YWVzLTEyOC1nY206dGVzdA@192.168.100.1:8888#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "ss://aes-128-gcm:test@192.168.100.1:8888"
    
    # 测试带插件的SS链接
    raw_link = "ss://YWVzLTI1Ni1nY206dGVzdA@192.168.100.1:8888/?plugin=obfs-local%3Bobfs%3Dhttp#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "ss://aes-256-gcm:test@192.168.100.1:8888"

def test_decode_ssr():
    # 测试基本SSR链接
    raw_link = "ssr://MTkyLjE2OC4xMDAuMTo4ODg4Om9yaWdpbjphZXMtMjU2LWNmYjpwbGFpbjpkR1Z6ZEEvP3JlbWFya3M9VW1WdFlYSnJjdw"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "ssr://aes-256-cfb:test@192.168.100.1:8888?protocol=origin&obfs=plain"
    
    # 测试完整SSR链接
    raw_link = "ssr://MTkyLjE2OC4xMDAuMTo4ODg4Om9yaWdpbjphZXMtMjU2LWNmYjpwbGFpbjpkR1Z6ZEE9PS8_b2Jmc3BhcmFtPWRHVnpkQT09JnByb3RvcGFyYW09ZEdWemRBPT0mcmVtYXJrcz1WR1Z6ZEE9PQ"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "ssr://aes-256-cfb:test@192.168.100.1:8888?protocol=origin&protocol_param=test&obfs=plain&obfs_param=test"

def test_decode_vmess():
    # 测试本VMess链接
    raw_link = "vmess://eyJhZGQiOiIxOTIuMTY4LjEwMC4xIiwiYWlkIjoiMCIsImhvc3QiOiIiLCJpZCI6IjEyMzQ1Njc4LWFiY2QtZWZnaCIsIm5ldCI6InRjcCIsInBhdGgiOiIiLCJwb3J0IjoiODg4OCIsInBzIjoiRXhhbXBsZSIsInNjeSI6ImF1dG8iLCJzbmkiOiIiLCJ0bHMiOiIiLCJ0eXBlIjoibm9uZSIsInYiOiIyIn0="
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "vmess://aes-128-gcm:12345678-abcd-efgh@192.168.100.1:8888?alterID=0"
    
    # 测试带TLS的VMess链接
    raw_link = "vmess://eyJhZGQiOiIxOTIuMTY4LjEwMC4xIiwiYWlkIjoiMCIsImhvc3QiOiIiLCJpZCI6IjEyMzQ1Njc4LWFiY2QtZWZnaCIsIm5ldCI6InRjcCIsInBhdGgiOiIiLCJwb3J0IjoiODg4OCIsInBzIjoiRXhhbXBsZSIsInNjeSI6ImFlcy0xMjgtZ2NtIiwic25pIjoiZXhhbXBsZS5jb20iLCJ0bHMiOiJ0bHMiLCJ0eXBlIjoibm9uZSIsInYiOiIyIn0="
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "tls://192.168.100.1:8888?serverName=example.com,vmess://aes-128-gcm:12345678-abcd-efgh@192.168.100.1:8888?alterID=0"
    
    # 测试带WebSocket的VMess链接
    raw_link = "vmess://eyJhZGQiOiIxOTIuMTY4LjEwMC4xIiwiYWlkIjoiMCIsImhvc3QiOiJleGFtcGxlLmNvbSIsImlkIjoiMTIzNDU2NzgtYWJjZC1lZmdoIiwibmV0Ijoid3MiLCJwYXRoIjoiL3BhdGgiLCJwb3J0IjoiODg4OCIsInBzIjoiRXhhbXBsZSIsInNjeSI6ImFlcy0xMjgtZ2NtIiwic25pIjoiIiwidGxzIjoiIiwidHlwZSI6Im5vbmUiLCJ2IjoiMiJ9"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "ws://@?path=/path&host=example.com,vmess://aes-128-gcm:12345678-abcd-efgh@192.168.100.1:8888?alterID=0"
    
    # 测试带TLS和WebSocket的VMess链接
    raw_link = "vmess://eyJhZGQiOiIxOTIuMTY4LjEwMC4xIiwiYWlkIjoiMCIsImhvc3QiOiJleGFtcGxlLmNvbSIsImlkIjoiMTIzNDU2NzgtYWJjZC1lZmdoIiwibmV0Ijoid3MiLCJwYXRoIjoiL3BhdGgiLCJwb3J0IjoiODg4OCIsInBzIjoiRXhhbXBsZSIsInNjeSI6ImFlcy0xMjgtZ2NtIiwic25pIjoiZXhhbXBsZS5jb20iLCJ0bHMiOiJ0bHMiLCJ0eXBlIjoibm9uZSIsInYiOiIyIn0="
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "tls://192.168.100.1:8888?serverName=example.com,ws://@?path=/path&host=example.com,vmess://aes-128-gcm:12345678-abcd-efgh@192.168.100.1:8888?alterID=0"

def test_decode_vless():
    """测试VLESS链接解码"""
    # 测试基本VLESS链接
    raw_link = "vless://12345678-abcd-efgh@192.168.100.1:8888?encryption=none&security=none&type=tcp#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "vless://12345678-abcd-efgh@192.168.100.1:8888"
    
    # 测试带TLS的VLESS链接
    raw_link = "vless://12345678-abcd-efgh@192.168.100.1:8888?encryption=none&security=tls&sni=example.com&type=tcp#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "tls://192.168.100.1:8888?serverName=example.com,vless://12345678-abcd-efgh@192.168.100.1:8888"
    
    # 测试带WebSocket的VLESS链接
    raw_link = "vless://12345678-abcd-efgh@192.168.100.1:8888?encryption=none&security=none&type=ws&host=example.com&path=/path#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "ws://@?path=/path&host=example.com,vless://12345678-abcd-efgh@192.168.100.1:8888"
    
    # 测试带TLS和WebSocket的VLESS链接
    raw_link = "vless://12345678-abcd-efgh@192.168.100.1:8888?encryption=none&security=tls&type=ws&host=example.com&path=/path&sni=example.com#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "tls://192.168.100.1:8888?serverName=example.com,ws://@?path=/path&host=example.com,vless://12345678-abcd-efgh@192.168.100.1:8888"
    
    # 测试带ALPN的VLESS链接
    raw_link = "vless://12345678-abcd-efgh@192.168.100.1:8888?encryption=none&security=tls&type=tcp&alpn=h2,http/1.1&sni=example.com#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "tls://192.168.100.1:8888?serverName=example.com&alpn=h2&alpn=http/1.1,vless://12345678-abcd-efgh@192.168.100.1:8888"
    
    # 测试单个ALPN的VLESS链接
    raw_link = "vless://12345678-abcd-efgh@192.168.100.1:8888?encryption=none&security=tls&type=tcp&alpn=h2&sni=example.com#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "tls://192.168.100.1:8888?serverName=example.com&alpn=h2,vless://12345678-abcd-efgh@192.168.100.1:8888"

def test_decode_trojan():
    # 测试基本Trojan链接
    raw_link = "trojan://password@192.168.100.1:8888#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "trojan://password@192.168.100.1:8888"
    
    # 测试带TLS的Trojan链接
    raw_link = "trojan://password@192.168.100.1:8888?security=tls&sni=example.com&allowInsecure=1#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "tls://192.168.100.1:8888?skipVerify=true&serverName=example.com,trojan://password@192.168.100.1:8888"
    
    # 测试带WebSocket的Trojan链接
    raw_link = "trojan://password@192.168.100.1:8888?type=ws&host=example.com&path=/path#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "ws://@?path=/path&host=example.com,trojan://password@192.168.100.1:8888"
    
    # 测试带TLS和WebSocket的Trojan链接
    raw_link = "trojan://password@192.168.100.1:8888?security=tls&type=ws&host=example.com&path=/path&sni=example.com#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "tls://192.168.100.1:8888?serverName=example.com,ws://@?path=/path&host=example.com,trojan://password@192.168.100.1:8888"

def test_decode_ssh():
    # 测试基本SSH链接
    raw_link = "ssh://user:pass@192.168.100.1:22"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "ssh://user:pass@192.168.100.1:22"
    
    # 测试带密钥的SSH链接
    raw_link = "ssh://192.168.100.1:22?key=/path/to/key"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    assert glider_link == "ssh://192.168.100.1:22?key=/path/to/key"

def test_invalid_decode():
    # 测试无效的代理信息
    with pytest.raises(ValueError, match="Invalid proxy info"):
        GliderDecoder.decode({})
    
    # 测试不支持的协议
    with pytest.raises(ValueError, match="Unsupported protocol"):
        GliderDecoder.decode({"proxy_protocol": "invalid"})
    
    # 测试缺少必需字段
    with pytest.raises(ValueError):
        GliderDecoder.decode({"proxy_protocol": "ss"})

def test_data_yes_links():
    """测试data目录的有效链接"""
    data_dir = Path(__file__).parent.parent / "data"
    
    # 只测试 *_yes.txt 文件
    for file in data_dir.glob("*_yes.txt"):
        protocol = file.name.split("_")[0]
        print(f"\nTesting {protocol} links from {file.name}")
        
        with open(file, "r", encoding="utf-8") as f:
            links = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            
        for link in links:
            try:
                # 解析为元信息
                proxy_info = ProxyParser.parse(link)
                # 转换为glider链接
                glider_link = GliderDecoder.decode(proxy_info)
                print(f"✓ {glider_link}")
            except Exception as e:
                print(f"\n✗ Failed to convert link:")
                print(f"  Original: {link}")
                print(f"  Error: {str(e)}")
                pytest.fail(f"Failed to convert link: {link}\nError: {str(e)}")

def test_decode_invalid_ws():
    """测试无效的WebSocket配置"""
    # 测试带逗号的path
    raw_link = "vless://12345678-abcd-efgh@192.168.100.1:8888?encryption=none&security=none&type=ws&host=example.com&path=/path,with,comma#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    # 由于path包含逗号，不应该生成ws传输层
    assert glider_link == "vless://12345678-abcd-efgh@192.168.100.1:8888"
    
    # 测试带TLS和带逗号的path
    raw_link = "vless://12345678-abcd-efgh@192.168.100.1:8888?encryption=none&security=tls&type=ws&host=example.com&path=/path,with,comma&sni=example.com#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    # 应该只有TLS层和裸协议层，没有ws层
    assert glider_link == "tls://192.168.100.1:8888?serverName=example.com,vless://12345678-abcd-efgh@192.168.100.1:8888"
    
    # 对VMess也进行同样的测试
    raw_link = "vmess://eyJhZGQiOiIxOTIuMTY4LjEwMC4xIiwiYWlkIjoiMCIsImhvc3QiOiJleGFtcGxlLmNvbSIsImlkIjoiMTIzNDU2NzgtYWJjZC1lZmdoIiwibmV0Ijoid3MiLCJwYXRoIjoiL3BhdGgsd2l0aCxjb21tYSIsInBvcnQiOiI4ODg4IiwicHMiOiJFeGFtcGxlIiwic2N5IjoiYWVzLTEyOC1nY20iLCJzbmkiOiJleGFtcGxlLmNvbSIsInRscyI6InRscyIsInR5cGUiOiJub25lIiwidiI6IjIifQ=="
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    # 应该只有TLS层和裸协议层，没有ws层
    assert glider_link == "tls://192.168.100.1:8888?serverName=example.com,vmess://aes-128-gcm:12345678-abcd-efgh@192.168.100.1:8888?alterID=0"
    
    # 对Trojan也进行同样的测试
    raw_link = "trojan://password@192.168.100.1:8888?security=tls&type=ws&host=example.com&path=/path,with,comma&sni=example.com#Example"
    proxy_info = ProxyParser.parse(raw_link)
    glider_link = GliderDecoder.decode(proxy_info)
    # 应该只有TLS层和裸协议层，没有ws层
    assert glider_link == "tls://192.168.100.1:8888?serverName=example.com,trojan://password@192.168.100.1:8888"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 