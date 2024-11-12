import json
from typing import List, Dict
from ..models.proxy import Proxy
from .constants import (
    SUPPORTED_SS_METHODS,
    SUPPORTED_PROTOCOLS,
    HTTP_HEADERS,
    DEFAULT_VALUES,
    TLS_FINGERPRINTS,
    ALPN_PROTOCOLS,
    CLEAN_FIELDS,
    SPECIAL_CHARS
)
from .string_cleaner import StringCleaner

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
            "inbounds": client_config.get('inbounds', []),
            "outbounds": [
                # 直连出站
                {
                    "tag": "direct",
                    "protocol": "freedom",
                    "settings": {}
                },
                # 拦截出站
                {
                    "tag": "block",
                    "protocol": "blackhole",
                    "settings": {}
                }
            ],
            "routing": {
                "domainStrategy": "IPOnDemand",
                "rules": [],
                "balancers": []  # 添加负载均衡器配置
            }
        }
        
        # 为每个站点创建专用的出站组
        all_outbound_tags = []  # 用于收集所有代理的标签
        
        for site, proxies in site_proxies.items():
            site_outbounds = []
            # 为站点的每个代理创建出站
            for i, proxy in enumerate(proxies):
                # 生成更有意义的标签
                tag = f"{site}_{proxy.proxy_type}_{i}"
                outbound = {
                    "tag": tag,
                    "protocol": "shadowsocks" if proxy.proxy_type == "ss" else proxy.proxy_type,
                    "settings": XrayConfigGenerator._generate_proxy_settings(proxy),
                    "streamSettings": XrayConfigGenerator._generate_stream_settings(proxy)
                }
                site_outbounds.append(outbound)
                config["outbounds"].append(outbound)
                all_outbound_tags.append(tag)
            
            # 如果站点有代理，创建负载均衡器
            if site_outbounds:
                balancer = {
                    "tag": f"{site}_balancer",
                    "selector": [f"{site}_"],  # 匹配前缀
                    "strategy": {
                        "type": "random"  # 使用随机策略
                    }
                }
                config["routing"]["balancers"].append(balancer)
        
        # 如果有代理，创建通用负载均衡器
        if all_outbound_tags:
            universal_balancer = {
                "tag": "universal_proxy",
                "selector": ["91mh01_", "www.wnacg.com_"],  # 匹配所有站点的代理
                "strategy": {
                    "type": "random"  # 使用随机策略
                }
            }
            config["routing"]["balancers"].append(universal_balancer)
        
        # 添加路由规则（按优先级排序）
        config["routing"]["rules"] = [
            # 优先级1：每个目标站点使用其专用代理
            *[{
                "type": "field",
                "domain": [site],
                "balancerTag": f"{site}_balancer"
            } for site in site_proxies.keys()],
            
            # 优先级2：阻止广告域名
            {
                "type": "field",
                "domain": ["geosite:category-ads-all"],
                "outboundTag": "block"
            },
            
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
        ]
        
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
                        "encryption": "none",  # VLESS必须设置为none
                        "flow": StringCleaner.clean_value(proxy.settings.get('flow', ''), 'flow')
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
            # 标准化加密方法名称
            method = proxy.settings['method'].lower()
            if method not in SUPPORTED_SS_METHODS:
                raise ValueError(f"Unsupported SS encryption method: {method}")
                
            return {
                "servers": [{
                    "address": proxy.server,
                    "port": proxy.port,
                    "method": SUPPORTED_SS_METHODS[method],
                    "password": proxy.settings['password'],
                    "level": 0
                }]
            }
        else:
            raise ValueError(f"Unsupported proxy type: {proxy.proxy_type}")
    
    @staticmethod
    def _generate_stream_settings(proxy: Proxy) -> Dict:
        """生成传输层设置"""
        # 使用StringCleaner处理transport_type
        transport_type = StringCleaner.clean_transport(proxy.settings.get('type', 'tcp'))
            
        # 使用StringCleaner处理security
        security = StringCleaner.clean_security(proxy.settings.get('security', 'none'), proxy.server)
            
        settings = {
            "network": transport_type,
            "security": security
        }
        
        # TLS设置
        if proxy.settings.get('tls') == 'tls' or security == 'tls':
            settings["security"] = "tls"
            settings["tlsSettings"] = {
                "serverName": StringCleaner.clean_host(proxy.settings.get('sni', ''), proxy.server),
                "allowInsecure": True,
                "fingerprint": StringCleaner.clean_value(proxy.settings.get('fp', 'chrome'), 'fp'),
                "alpn": ["h2", "http/1.1"]
            }
        
        # Reality设置
        elif security == 'reality':
            settings["security"] = "reality"
            settings["realitySettings"] = {
                "serverName": StringCleaner.clean_host(proxy.settings.get('sni', ''), proxy.server),
                "fingerprint": StringCleaner.clean_value(proxy.settings.get('fp', 'chrome'), 'fp'),
                "publicKey": StringCleaner.clean_value(proxy.settings.get('pbk', ''), 'pbk'),
                "shortId": StringCleaner.clean_value(proxy.settings.get('sid', ''), 'sid'),
                "spiderX": StringCleaner.clean_value(proxy.settings.get('spx', ''), 'spx')
            }
        
        # 传输层设置
        if transport_type == "ws":
            settings["wsSettings"] = {
                "path": StringCleaner.clean_path(proxy.settings.get('path', '/')),
                "headers": {
                    "Host": StringCleaner.clean_host(proxy.settings.get('host', ''), proxy.server)
                }
            }
        elif transport_type == "grpc":
            settings["grpcSettings"] = {
                "serviceName": StringCleaner.clean_value(proxy.settings.get('serviceName', ''), 'serviceName'),
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
                            "path": [StringCleaner.clean_path(proxy.settings.get('path', '/'))],
                            "headers": StringCleaner.clean_headers(HTTP_HEADERS, proxy.server)
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