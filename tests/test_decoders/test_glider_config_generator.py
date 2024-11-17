import pytest
from pathlib import Path
from src.decoders.glider_config_generator import GliderConfigGenerator

def test_generate_config(tmp_path):
    """测试生成glider配置文件"""
    # 使用临时目录
    output_file = tmp_path / "glider.conf"
    
    # 生成配置
    GliderConfigGenerator.generate(output_file=str(output_file))
    
    # 验证文件存在
    assert output_file.exists()
    
    # 读取配置内容
    content = output_file.read_text()
    
    # 验证基本配置
    assert "verbose=True" in content
    assert "listen=:7630" in content
    assert "strategy=lha" in content
    assert "check=http://www.msftconnecttest.com/connecttest.txt#expect=200" in content
    assert "checkinterval=30" in content
    
    # 验证代理配置
    lines = content.split("\n")
    forward_lines = [line for line in lines if line.startswith("forward=")]
    
    # 确保有代理配置
    assert len(forward_lines) > 0
    
    # 验证代理格式
    for line in forward_lines:
        assert line.startswith("forward=")
        protocol = line.split("://")[0].split("=")[1]
        assert protocol in ["ss", "ssr", "vmess", "vless", "trojan", "ssh"]

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 