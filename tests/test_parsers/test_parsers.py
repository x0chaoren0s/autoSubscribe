import pytest
from src.parsers import BaseParser, Base64Parser, LineParser

def test_base_parser():
    """测试基础解析器"""
    parser = BaseParser()
    with pytest.raises(NotImplementedError):
        parser.parse("test")

def test_line_parser():
    """测试行解析器"""
    parser = LineParser()
    
    # 测试空内容
    assert parser.parse("") == []
    
    # 测试单行内容
    content = "ss://test"
    assert parser.parse(content) == ["ss://test"]
    
    # 测试多行内容
    content = """
    ss://test1
    vmess://test2
    
    trojan://test3
    """
    assert parser.parse(content) == ["ss://test1", "vmess://test2", "trojan://test3"]
    
    # 测试各种注释情况
    content = """
    # 这是一个纯注释行
    ss://test1#remark # 这是行内注释
    vmess://test2#tag#1 # 这也是行内注释
    trojan://test3#remark%20name # 注释
    vless://test4#remark%20with%20spaces#2
    # 这是另一个纯注释行
    ssh://test5 # 注释包含#号#号
    ss://test6#remark #这个注释紧贴着链接
    """
    assert parser.parse(content) == [
        "ss://test1#remark",
        "vmess://test2#tag#1",
        "trojan://test3#remark%20name",
        "vless://test4#remark%20with%20spaces",
        "ssh://test5",
        "ss://test6#remark"
    ]
    
    # 测试特殊情况
    content = """
    ###这是注释
    ss://test#remark###这是注释
    vmess://test#remark  ###这是注释
    ss://test  #remark#这是注释
    #ss://test#这是注释掉的链接
    not-a-proxy-link
    """
    assert parser.parse(content) == [
        "ss://test#remark",
        "vmess://test#remark",
        "ss://test"
    ]
    
    # 测试无效内容
    with pytest.raises(ValueError):
        parser.parse(None)

def test_base64_parser():
    """测试Base64解析器"""
    parser = Base64Parser()
    
    # 测试空内容
    assert parser.parse("") == []
    
    # 测试单行内容
    content = "c3M6Ly90ZXN0"  # base64("ss://test")
    assert parser.parse(content) == ["ss://test"]
    
    # 测试多行内容
    content = """
    c3M6Ly90ZXN0MQp2bWVzczovL3Rlc3QyCnRyb2phbjovL3Rlc3Qz
    """.strip()  # base64("ss://test1\nvmess://test2\ntrojan://test3")
    assert parser.parse(content) == ["ss://test1", "vmess://test2", "trojan://test3"]
    
    # 测试带填充的Base64
    content = "c3M6Ly90ZXN0"  # 不带填充
    content_padded = "c3M6Ly90ZXN0=="  # 带填充
    assert parser.parse(content) == parser.parse(content_padded)
    
    # 测试无效的Base64内容
    with pytest.raises(ValueError):
        parser.parse("invalid base64!")
    
    # 测试无效内容
    with pytest.raises(ValueError):
        parser.parse(None)
    
    # 测试Base64编码的带注释内容
    content = """
    IyDov5nmmK/ms6jph4oKc3M6Ly90ZXN0MSAgIyDov5nmmK9TU+iKgueCuQoKIyBWTWVzc+iKgueCuQp2bWVzczovL3Rlc3QyCiN0cm9qYW46Ly9jb21tZW50ZWQK
    """.strip()  # base64编码的带注释内容
    links = parser.parse(content)
    assert "ss://test1" in links
    assert "vmess://test2" in links
    assert "trojan://commented" not in links

def test_subscription_content():
    """测试实际的订阅内容场景"""
    # Base64编码的订阅内容
    base64_content = """
    IyDorr7lpIdBCiMg5rWL6K+V6IqC54K5CnZtZXNzOi8vZXlKMklqb2lNaUlzSW1Ga1pDSTZJbmQzZHk1amIyMWxJaXdpY0c5eWRDSTZJamd3SWl3aWFXUWlPaUl4TWpNaWZRPT0KCiMg6K6+5aSHQgpzczovL1lXVnpMVEV5T0MxblkyMDZkR1Z6ZEE9PQo=
    """.strip()  # 包含注释的Base64编码内容
    
    # 普通文本的订阅内容
    text_content = """
    # 节点列表
    ss://YWVzLTEyOC1nY206dGVzdA@192.168.1.1:8388#Example1
    
    # VMess节点
    vmess://eyJ2IjoiMiIsInBzIjoidGVzdCJ9
    
    # Trojan节点
    trojan://password@example.com:443
    
    # 已弃用的节点
    #ss://deprecated
    #vmess://old-node
    """
    
    # 测试Base64解析器
    base64_parser = Base64Parser()
    links = base64_parser.parse(base64_content)
    assert len(links) > 0
    assert all(link.startswith(('ss://', 'vmess://', 'trojan://', 'vless://', 'ssh://')) for link in links)
    
    # 测试行解析器
    line_parser = LineParser()
    links = line_parser.parse(text_content)
    assert len(links) == 3
    assert links[0].startswith('ss://')
    assert links[1].startswith('vmess://')
    assert links[2].startswith('trojan://')
    assert not any('deprecated' in link for link in links)
    assert not any('old-node' in link for link in links)

if __name__ == "__main__":
    pytest.main([__file__, "-vv"]) 