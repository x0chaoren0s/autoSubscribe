import pytest
from src.utils.glider_config_generator import GliderConfigGenerator
from src.utils.xray_config_generator import XrayConfigGenerator
from src.encoders.encoder import ProxyEncoder

def test_glider_config_generator():
    """测试Glider配置生成器"""
    # 准备测试数据
    raw_links = {
        "example.com": [
            "ss://YWVzLTEyOC1nY206dGVzdA@192.168.1.1:8388#SS节点",
            "vmess://eyJhZGQiOiIxOTIuMTY4LjEuMiIsImFpZCI6IjAiLCJob3N0IjoiIiwiaWQiOiIxMjM0NTY3OC1hYmNkLWVmZ2giLCJuZXQiOiJ0Y3AiLCJwYXRoIjoiIiwicG9ydCI6IjQ0MyIsInBzIjoiVk1lc3Poh6rliqjnvZEiLCJzY3kiOiJhdXRvIiwic25pIjoiIiwidGxzIjoiIiwidHlwZSI6Im5vbmUiLCJ2IjoiMiJ9",
            "trojan://password@192.168.1.3:443?security=tls&sni=example.com#Trojan节点"
        ]
    }
    
    # 转换为元信息字典
    site_proxies = {
        site: [ProxyEncoder.encode(link) for link in links]
        for site, links in raw_links.items()
    }
    
    # 准备客户端配置
    client_config = {
        "listen": ":1080",
        "strategy": "rr",
        "check_url": "http://www.google.com",
        "check_interval": 30,
        "target_hosts": {
            "example.com": {
                "display_name": "示例站点",
                "host": "example.com"
            }
        }
    }
    
    # 生成配置
    config = GliderConfigGenerator.generate_client_config(site_proxies, client_config)
    
    # 验证基本配置
    assert "verbose=True" in config
    assert "listen=:1080" in config
    assert "strategy=rr" in config
    assert "check=http://www.google.com" in config
    assert "checkinterval=30" in config
    
    # 验证代理配置
    assert "# 示例站点" in config
    assert "forward=ss://" in config
    assert "forward=vmess://" in config
    assert "forward=trojan://" in config
    
    # 生成规则文件
    rules = GliderConfigGenerator.generate_rule_files(site_proxies, client_config)
    
    # 验证规则文件
    assert "example.com.rule" in rules
    rule_content = rules["example.com.rule"]
    assert "# Rules for 示例站点" in rule_content
    assert "domain=*.example.com proxy" in rule_content

def test_xray_config_generator():
    """测试Xray配置生成器"""
    # 准备测试数据
    raw_links = {
        "example.com": [
            "ss://YWVzLTEyOC1nY206dGVzdA@192.168.1.1:8388#SS节点",
            "vmess://eyJhZGQiOiIxOTIuMTY4LjEuMiIsImFpZCI6IjAiLCJob3N0IjoiIiwiaWQiOiIxMjM0NTY3OC1hYmNkLWVmZ2giLCJuZXQiOiJ0Y3AiLCJwYXRoIjoiIiwicG9ydCI6IjQ0MyIsInBzIjoiVk1lc3Poh6rliqjnvZEiLCJzY3kiOiJhdXRvIiwic25pIjoiIiwidGxzIjoiIiwidHlwZSI6Im5vbmUiLCJ2IjoiMiJ9",
            "trojan://password@192.168.1.3:443?security=tls&sni=example.com#Trojan节点",
            "ssh://user:pass@192.168.1.4:22"  # 这个应该被忽略
        ]
    }
    
    # 转换为元信息字典
    site_proxies = {
        site: [ProxyEncoder.encode(link) for link in links]
        for site, links in raw_links.items()
    }
    
    # 准备客户端配置
    client_config = {
        "inbounds": [
            {
                "protocol": "socks",
                "port": 1080,
                "listen": "127.0.0.1",
                "settings": {
                    "auth": "password",
                    "accounts": [
                        {
                            "user": "user",
                            "pass": "pass"
                        }
                    ]
                }
            },
            {
                "protocol": "http",
                "port": 1081,
                "listen": "127.0.0.1"
            }
        ],
        "target_hosts": {
            "example.com": {
                "display_name": "示例站点",
                "host": "example.com"
            }
        }
    }
    
    # 生成配置
    config = XrayConfigGenerator.generate_client_config(site_proxies, client_config)
    
    # 验证基本结构
    assert "log" in config
    assert "inbounds" in config
    assert "outbounds" in config
    assert "routing" in config
    
    # 验证入站配置
    inbounds = config["inbounds"]
    assert len(inbounds) == 2
    assert inbounds[0]["protocol"] == "socks"
    assert inbounds[0]["port"] == 1080
    assert inbounds[1]["protocol"] == "http"
    assert inbounds[1]["port"] == 1081
    
    # 验证出站配置
    outbounds = config["outbounds"]
    assert len(outbounds) > 3  # direct, block, 和至少一个代理出站
    assert outbounds[0]["protocol"] == "freedom"
    assert outbounds[1]["protocol"] == "blackhole"
    
    # 找到代理出站
    proxy_outbound = next(
        (o for o in outbounds if o["tag"].startswith("proxy-")),
        None
    )
    assert proxy_outbound is not None
    assert proxy_outbound["protocol"] == "selector"
    
    # 验证服务器配置
    servers = proxy_outbound["settings"]["servers"]
    assert len(servers) == 3  # ss, vmess, trojan，不包括ssh
    
    # 验证路由规则
    rules = config["routing"]["rules"]
    assert len(rules) > 0
    # 验证站点规则
    site_rule = next(
        (r for r in rules if "domain:*.example.com" in r.get("domain", [])),
        None
    )
    assert site_rule is not None
    # 验证默认规则
    assert any("geosite:cn" in r.get("domain", []) for r in rules)
    assert any("geoip:cn" in r.get("ip", []) for r in rules)

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 