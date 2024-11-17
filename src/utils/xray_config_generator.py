from typing import Dict, List, Any
import json
import uuid

class XrayConfigGenerator:
    """Xray配置生成器"""
    
    @staticmethod
    def generate_client_config(site_proxies: Dict[str, List[Dict[str, Any]]], client_config: Dict) -> Dict:
        """生成Xray客户端配置"""
        config = {
            "log": {
                "loglevel": "warning"
            },
            "inbounds": [],
            "outbounds": [
                {
                    "protocol": "freedom",
                    "tag": "direct"
                },
                {
                    "protocol": "blackhole",
                    "tag": "block"
                }
            ],
            "routing": {
                "domainStrategy": "IPIfNonMatch",
                "rules": []
            }
        }
        
        # 添加入站配置
        for inbound in client_config['inbounds']:
            config['inbounds'].append(XrayConfigGenerator._generate_inbound(inbound))
        
        # 为每个站点生成出站配置
        outbound_tags = []
        for site, proxies in site_proxies.items():
            if not proxies:
                continue
                
            # 获取站点配置
            site_config = client_config['target_hosts'].get(site, {})
            site_name = site_config.get('display_name', site)
            
            # 生成出站配置
            outbound = XrayConfigGenerator._generate_outbound(proxies, site)
            if outbound:
                config['outbounds'].append(outbound)
                outbound_tags.append(outbound['tag'])
                
                # 添加路由规则
                config['routing']['rules'].append({
                    "type": "field",
                    "domain": [f"domain:*.{site}"],
                    "outboundTag": outbound['tag']
                })
        
        # 添加默认路由规则
        config['routing']['rules'].extend([
            {
                "type": "field",
                "domain": ["geosite:category-ads-all"],
                "outboundTag": "block"
            },
            {
                "type": "field",
                "domain": ["geosite:cn"],
                "outboundTag": "direct"
            },
            {
                "type": "field",
                "ip": ["geoip:cn"],
                "outboundTag": "direct"
            }
        ])
        
        return config
    
    @staticmethod
    def _generate_inbound(inbound_config: Dict) -> Dict:
        """生成入站配置"""
        inbound = {
            "listen": inbound_config.get('listen', '127.0.0.1'),
            "port": inbound_config['port'],
            "protocol": inbound_config['protocol'],
            "tag": inbound_config.get('tag', f"inbound-{inbound_config['port']}")
        }
        
        # 添加协议特定设置
        if inbound['protocol'] == 'socks':
            inbound['settings'] = {
                "auth": inbound_config.get('settings', {}).get('auth', 'noauth'),
                "udp": True
            }
            if inbound['settings']['auth'] == 'password':
                inbound['settings']['accounts'] = inbound_config['settings']['accounts']
                
        elif inbound['protocol'] == 'http':
            inbound['settings'] = {}
            if inbound_config.get('settings', {}).get('auth') == 'password':
                inbound['settings']['accounts'] = inbound_config['settings']['accounts']
        
        return inbound
    
    @staticmethod
    def _generate_outbound(proxies: List[Dict[str, Any]], tag: str) -> Dict:
        """生成出站配置"""
        # 过滤出支持的代理
        supported_proxies = [p for p in proxies if p['proxy_protocol'].value in ('ss', 'vmess', 'vless', 'trojan')]
        if not supported_proxies:
            return None
            
        # 创建负载均衡配置
        return {
            "protocol": "selector",
            "tag": f"proxy-{tag}",
            "settings": {
                "servers": [
                    XrayConfigGenerator._generate_server_config(proxy)
                    for proxy in supported_proxies
                ]
            }
        }
    
    @staticmethod
    def _generate_server_config(proxy: Dict[str, Any]) -> Dict:
        """生成服务器配置"""
        protocol = proxy['proxy_protocol'].value
        
        if protocol == 'ss':
            return {
                "address": proxy['server'],
                "port": proxy['port'],
                "method": proxy['method'],
                "password": proxy['password']
            }
            
        elif protocol == 'vmess':
            return {
                "address": proxy['server'],
                "port": proxy['port'],
                "users": [{
                    "id": proxy['id'],
                    "alterId": proxy.get('aid', 0),
                    "security": proxy.get('security', 'auto')
                }]
            }
            
        elif protocol == 'vless':
            return {
                "address": proxy['server'],
                "port": proxy['port'],
                "users": [{
                    "id": proxy['id'],
                    "encryption": proxy.get('encryption', 'none')
                }]
            }
            
        elif protocol == 'trojan':
            return {
                "address": proxy['server'],
                "port": proxy['port'],
                "password": proxy['password']
            }
            
        return None