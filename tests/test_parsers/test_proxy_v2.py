import pytest
from src.models.proxy_v2 import ProxyParser, ProxyType

def test_parse_ss():
    # 测试 SIP002 格式
    link = "ss://YWVzLTEyOC1nY206dGVzdA@192.168.100.1:8888#Example"
    info = ProxyParser.parse(link)
    assert info["proxy_protocol"] == ProxyType.SS
    assert info["server"] == "192.168.100.1"
    assert info["port"] == 8888
    assert info["method"] == "aes-128-gcm"
    assert info["password"] == "test"
    assert info["name"] == "Example"
    
    # 测试传统格式
    link = "ss://YWVzLTEyOC1nY206dGVzdEAxOTIuMTY4LjEwMC4xOjg4ODg"
    info = ProxyParser.parse(link)
    assert info["proxy_protocol"] == ProxyType.SS
    assert info["server"] == "192.168.100.1"
    assert info["port"] == 8888
    assert info["method"] == "aes-128-gcm"
    assert info["password"] == "test"

def test_parse_ssr():
    link = "ssr://MTkyLjE2OC4xMDAuMTo4ODg4Om9yaWdpbjphZXMtMjU2LWNmYjpwbGFpbjpkR1Z6ZEEvP3JlbWFya3M9VW1WdFlYSnJjdw"
    info = ProxyParser.parse(link)
    assert info["proxy_protocol"] == ProxyType.SSR
    assert info["server"] == "192.168.100.1"
    assert info["port"] == 8888
    assert info["protocol"] == "origin"
    assert info["method"] == "aes-256-cfb"
    assert info["password"] == "test"
    assert info["name"] == "Remarks"

def test_parse_vmess():
    link = "vmess://eyJhZGQiOiIxOTIuMTY4LjEwMC4xIiwiYWlkIjoiMCIsImhvc3QiOiIiLCJpZCI6IjEyMzQ1Njc4LWFiY2QtZWZnaCIsIm5ldCI6InRjcCIsInBhdGgiOiIiLCJwb3J0IjoiODg4OCIsInBzIjoiRXhhbXBsZSIsInNjeSI6ImF1dG8iLCJzbmkiOiIiLCJ0bHMiOiIiLCJ0eXBlIjoibm9uZSIsInYiOiIyIn0="
    info = ProxyParser.parse(link)
    assert info["proxy_protocol"] == ProxyType.VMESS
    assert info["server"] == "192.168.100.1"
    assert info["port"] == 8888
    assert info["id"] == "12345678-abcd-efgh"
    assert info["aid"] == 0
    assert info["net"] == "tcp"
    assert info["name"] == "Example"

def test_parse_vless():
    link = "vless://12345678-abcd-efgh@192.168.100.1:8888?encryption=none&security=tls&sni=example.com#Example"
    info = ProxyParser.parse(link)
    assert info["proxy_protocol"] == ProxyType.VLESS
    assert info["server"] == "192.168.100.1"
    assert info["port"] == 8888
    assert info["id"] == "12345678-abcd-efgh"
    assert info["encryption"] == "none"
    assert info["security"] == "tls"
    assert info["sni"] == "example.com"
    assert info["name"] == "Example"

def test_parse_trojan():
    link = "trojan://password@192.168.100.1:8888?security=tls&sni=example.com#Example"
    info = ProxyParser.parse(link)
    assert info["proxy_protocol"] == ProxyType.TROJAN
    assert info["server"] == "192.168.100.1"
    assert info["port"] == 8888
    assert info["password"] == "password"
    assert info["sni"] == "example.com"
    assert info["name"] == "Example"

def test_parse_ssh():
    # 测试基本格式
    link = "ssh://user:pass@192.168.100.1:22"
    info = ProxyParser.parse(link)
    assert info["proxy_protocol"] == ProxyType.SSH
    assert info["server"] == "192.168.100.1"
    assert info["port"] == "22"
    assert info["username"] == "user"
    assert info["password"] == "pass"
    
    # 测试带参数格式
    link = "ssh://192.168.100.1?key=/path/to/key&ssh_ServerAliveInterval=60"
    info = ProxyParser.parse(link)
    assert info["proxy_protocol"] == ProxyType.SSH
    assert info["server"] == "192.168.100.1"
    assert info["port"] == "22"
    assert info["private_key"] == "/path/to/key"
    assert info["ssh_options"]["ServerAliveInterval"] == "60"

def test_invalid_links():
    # 测试无效链接
    invalid_links = [
        "",
        "invalid://link",
        "ss://invalid",
        "vmess://invalid",
    ]
    
    for link in invalid_links:
        with pytest.raises(ValueError):
            ProxyParser.parse(link) 

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 
    print(ProxyParser.parse("vmess://eyJhZGQiOiIxOTIuMTY4LjEwMC4xIiwiYWlkIjoiMCIsImhvc3QiOiIiLCJpZCI6IjEyMzQ1Njc4LWFiY2QtZWZnaCIsIm5ldCI6InRjcCIsInBhdGgiOiIiLCJwb3J0IjoiODg4OCIsInBzIjoiRXhhbXBsZSIsInNjeSI6ImF1dG8iLCJzbmkiOiIiLCJ0bHMiOiIiLCJ0eXBlIjoibm9uZSIsInYiOiIyIn0="))
    print(ProxyParser.parse("vmess://eyJhZGQiOiIxOTIuMTY4LjEwMC4xIiwiYWlkIjoiMCIsImhvc3QiOiJleGFtcGxlLmNvbSIsImlkIjoiMTIzNDU2NzgtYWJjZC1lZmdoIiwibmV0Ijoid3MiLCJwYXRoIjoiL3BhdGgiLCJwb3J0IjoiODg4OCIsInBzIjoiRXhhbXBsZSIsInNjeSI6ImFlcy0xMjgtZ2NtIiwic25pIjoiIiwidGxzIjoiIiwidHlwZSI6Im5vbmUiLCJ2IjoiMiJ9"))
