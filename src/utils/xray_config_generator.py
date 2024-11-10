import json
from typing import List, Dict
from ..models.proxy import Proxy

class XrayConfigGenerator:
    """生成完整的Xray配置"""
    
    @staticmethod
    def generate_client_config(site_proxies: Dict[str, List[Proxy]], client_config: dict) -> dict:
        """
        生成客户端配置
        
        Args:
            site_proxies: 每个站点的可用代理列表，格式为 {site: [proxies]}
            client_config: 客户端配置字典
            
        Returns:
            dict: Xray配置字典
        """
        # 基础配置
        config = {
            "log": {
                "loglevel": client_config.get('settings', {}).get('log_level', 'warning'),
                "access": "none"
            },
            "dns": client_config.get('dns', {
                "servers": [
                    "1.1.1.1",
                    "8.8.8.8",
                    {
                        "address": "114.114.114.114",
                        "port": 53,
                        "domains": ["geosite:cn"]
                    }
                ],
                "queryStrategy": "UseIPv4"
            }),
            "inbounds": client_config.get('inbounds', [{
                "tag": "socks",
                "port": 1080,
                "protocol": "socks",
                "settings": {
                    "auth": "noauth",
                    "udp": True,
                    "ip": "127.0.0.1"
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls", "quic"],
                    "metadataOnly": False
                }
            }]),
            "outbounds": [],
            "routing": {
                "domainStrategy": "IPOnDemand",
                "rules": []
            }
        }
        
        # 为每个站点创建专用的出站组
        for site, proxies in site_proxies.items():
            site_outbounds = []
            # 为站点的每个代理创建出站
            for i, proxy in enumerate(proxies):
                # 生成更有意义的标签
                tag = f"{site}_{proxy.proxy_type}_{i}"
                outbound = {
                    "tag": tag,
                    "protocol": proxy.proxy_type,
                    "settings": XrayConfigGenerator._generate_proxy_settings(proxy),
                    "streamSettings": XrayConfigGenerator._generate_stream_settings(proxy)
                }
                site_outbounds.append(outbound)
                config["outbounds"].append(outbound)
            
            # 为站点创建负载均衡器
            if site_outbounds:
                balancer_outbound = {
                    "tag": f"{site}_balancer",
                    "protocol": "balancer",
                    "settings": {
                        "strategy": {
                            "type": "leastPing"
                        },
                        "tags": [ob["tag"] for ob in site_outbounds],
                        "probeInterval": "10s"
                    }
                }
                config["outbounds"].append(balancer_outbound)
                
                # 添加站点特定的路由规则
                config["routing"]["rules"].append({
                    "type": "field",
                    "domain": [site],
                    "balancerTag": f"{site}_balancer"
                })
        
        # 添加直连出站
        direct_outbound = {
            "tag": "direct",
            "protocol": "freedom",
            "settings": {
                "domainStrategy": "UseIPv4"
            }
        }
        config["outbounds"].append(direct_outbound)
        
        # 添加阻止出站
        block_outbound = {
            "tag": "block",
            "protocol": "blackhole",
            "settings": {}
        }
        config["outbounds"].append(block_outbound)
        
        # 创建一个通用的负载均衡器，使用所有代理
        all_outbound_tags = []
        for outbound in config["outbounds"]:
            if any(site in outbound["tag"] for site in site_proxies.keys()):
                all_outbound_tags.append(outbound["tag"])
        
        if all_outbound_tags:
            # 添加通用负载均衡器
            universal_balancer = {
                "tag": "universal_proxy",
                "protocol": "balancer",
                "settings": {
                    "strategy": {
                        "type": "leastPing"
                    },
                    "tags": all_outbound_tags,
                    "probeInterval": "10s"
                }
            }
            config["outbounds"].append(universal_balancer)
        
        # 添加其他路由规则
        config["routing"]["rules"].extend([
            # 优先级1：阻止广告域名
            {
                "type": "field",
                "domain": ["geosite:category-ads-all"],
                "outboundTag": "block"
            },
            # 优先级2：每个目标站点使用其专用代理
            *[{
                "type": "field",
                "domain": [site],
                "balancerTag": f"{site}_balancer"
            } for site in site_proxies.keys()],
            # 优先级3：直连中国大陆域名
            {
                "type": "field",
                "domain": ["geosite:cn"],
                "outboundTag": "direct"
            },
            # 优先级4：直连中国大陆IP
            {
                "type": "field",
                "ip": ["geoip:cn", "geoip:private"],
                "outboundTag": "direct"
            },
            # 优先级5：其他流量使用所有代理的并集
            {
                "type": "field",
                "network": "tcp,udp",
                "balancerTag": "universal_proxy"
            }
        ])
        
        return config
    
    @staticmethod
    def _generate_proxy_settings(proxy: Proxy) -> dict:
        """生成代理设置"""
        if proxy.proxy_type == "vmess":
            return {
                "vnext": [{
                    "address": proxy.server,
                    "port": proxy.port,
                    "users": [{
                        "id": proxy.settings['id'],
                        "alterId": int(proxy.settings.get('aid', 0))
                    }]
                }]
            }
        elif proxy.proxy_type == "vless":
            return {
                "vnext": [{
                    "address": proxy.server,
                    "port": proxy.port,
                    "users": [{
                        "id": proxy.settings['uuid'],
                        "encryption": proxy.settings.get('encryption', 'none')
                    }]
                }]
            }
        elif proxy.proxy_type == "trojan":
            return {
                "servers": [{
                    "address": proxy.server,
                    "port": proxy.port,
                    "password": proxy.settings['password']
                }]
            }
        elif proxy.proxy_type == "ss":
            return {
                "servers": [{
                    "address": proxy.server,
                    "port": proxy.port,
                    "method": proxy.settings['method'],
                    "password": proxy.settings['password']
                }]
            }
        else:
            raise ValueError(f"Unsupported proxy type: {proxy.proxy_type}")
    
    @staticmethod
    def _generate_stream_settings(proxy: Proxy) -> dict:
        """生成传输层设置"""
        transport_type = proxy.settings.get('type', 'tcp')
        settings = {
            "network": transport_type,
            "security": proxy.settings.get('security', 'none')
        }
        
        # TLS设置
        if proxy.settings.get('tls') == 'tls' or proxy.settings.get('security') == 'tls':
            settings["security"] = "tls"
            settings["tlsSettings"] = {
                "serverName": proxy.settings.get('sni', proxy.server),
                "allowInsecure": True,
                "fingerprint": proxy.settings.get('fp', 'chrome'),
                "alpn": ["h2", "http/1.1"]
            }
        
        # Reality设置
        elif proxy.settings.get('security') == 'reality':
            settings["security"] = "reality"
            settings["realitySettings"] = {
                "serverName": proxy.settings.get('sni', ''),
                "fingerprint": proxy.settings.get('fp', 'chrome'),
                "publicKey": proxy.settings.get('pbk', ''),
                "shortId": proxy.settings.get('sid', ''),
                "spiderX": proxy.settings.get('spx', '')
            }
        
        # 传输层设置
        if transport_type == "ws":
            settings["wsSettings"] = {
                "path": proxy.settings.get('path', '/'),
                "headers": {
                    "Host": proxy.settings.get('host', proxy.server)
                }
            }
        elif transport_type == "grpc":
            settings["grpcSettings"] = {
                "serviceName": proxy.settings.get('serviceName', ''),
                "multiMode": proxy.settings.get('mode', 'gun') == 'multi'
            }
        elif transport_type == "tcp":
            if proxy.settings.get('headerType') == 'http':
                settings["tcpSettings"] = {
                    "header": {
                        "type": "http",
                        "request": {
                            "version": "1.1",
                            "method": "GET",
                            "path": [proxy.settings.get('path', '/')],
                            "headers": {
                                "Host": [proxy.settings.get('host', proxy.server)],
                                "User-Agent": ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"],
                                "Accept-Encoding": ["gzip, deflate"],
                                "Connection": ["keep-alive"],
                                "Pragma": "no-cache"
                            }
                        }
                    }
                }
            else:
                settings["tcpSettings"] = {
                    "header": {
                        "type": "none"
                    }
                }
        
        return settings 