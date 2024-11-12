from typing import Dict, List
from ..models.proxy import Proxy
from .constants import (
    SUPPORTED_SS_METHODS,
    SUPPORTED_PROTOCOLS,
    HTTP_HEADERS,
    DEFAULT_VALUES,
    TLS_FINGERPRINTS,
    ALPN_PROTOCOLS,
    GLIDER_DEFAULTS,
    GLIDER_CHECK_SETTINGS,
    GLIDER_DNS_SETTINGS,
    GLIDER_PROTOCOLS,
    GLIDER_RULE_TYPES,
    GLIDER_STRATEGIES
)
from .string_cleaner import StringCleaner

class GliderConfigGenerator:
    """生成Glider配置"""
    
    @staticmethod
    def generate_client_config(site_proxies: Dict[str, List[Proxy]], client_config: dict) -> str:
        """生成客户端配置"""
        config_lines = []
        settings = client_config.get('settings', {})
        
        # 添加verbose模式
        if settings.get('glider_verbose', GLIDER_DEFAULTS['verbose']):
            config_lines.append("# verbose mode, print logs")
            config_lines.append("verbose")
            config_lines.append("")
        
        # 添加监听器配置
        config_lines.append("# Listener Settings")
        for inbound in client_config.get('inbounds', []):
            if inbound['protocol'] == 'socks':
                listen = f"mixed://{inbound['listen']}:{inbound['port']}"
                if inbound.get('settings', {}).get('auth') == 'password':
                    user = inbound['settings']['accounts'][0]['user']
                    password = inbound['settings']['accounts'][0]['pass']
                    listen += f"?username={user}&password={password}"
                config_lines.append(f"listen={listen}")
            elif inbound['protocol'] == 'http':
                config_lines.append(f"listen=http://{inbound['listen']}:{inbound['port']}")
        config_lines.append("")
        
        # DNS配置
        dns_config = client_config.get('dns', {})
        if dns_config:
            config_lines.append("# DNS Settings")
            config_lines.append("dns=:53")  # 本地DNS服务器
            for server in dns_config.get('servers', []):
                if isinstance(server, str):
                    config_lines.append(f"dnsserver={server}:53")
                else:
                    config_lines.append(f"dnsserver={server['address']}:{server.get('port', 53)}")
            
            # DNS高级设置
            if settings.get('glider_dns_always_tcp', GLIDER_DNS_SETTINGS['always_tcp']):
                config_lines.append("dnsalwaystcp=true")
            if settings.get('glider_dns_no_aaaa', GLIDER_DNS_SETTINGS['no_aaaa']):
                config_lines.append("dnsnoaaaa=true")
            if settings.get('glider_dns_cache_size', GLIDER_DNS_SETTINGS['cache_size']):
                config_lines.append(f"dnscachesize={settings.get('glider_dns_cache_size', GLIDER_DNS_SETTINGS['cache_size'])}")
            if settings.get('glider_dns_max_ttl', GLIDER_DNS_SETTINGS['max_ttl']):
                config_lines.append(f"dnsmaxttl={settings.get('glider_dns_max_ttl', GLIDER_DNS_SETTINGS['max_ttl'])}")
            if settings.get('glider_dns_min_ttl', GLIDER_DNS_SETTINGS['min_ttl']):
                config_lines.append(f"dnsminttl={settings.get('glider_dns_min_ttl', GLIDER_DNS_SETTINGS['min_ttl'])}")
            config_lines.append("")
        
        # 添加检查设置
        config_lines.append("# Check Settings")
        check_url = settings.get('glider_check_url', GLIDER_CHECK_SETTINGS['url'])
        check_expect = settings.get('glider_check_expect', GLIDER_CHECK_SETTINGS['expect'])
        config_lines.append(f"check={check_url}#expect={check_expect}")
        config_lines.append(f"checkinterval={settings.get('glider_check_interval', GLIDER_CHECK_SETTINGS['interval'])}")
        config_lines.append(f"checktimeout={settings.get('glider_check_timeout', GLIDER_CHECK_SETTINGS['timeout'])}")
        config_lines.append(f"maxfailures={settings.get('glider_max_failures', GLIDER_CHECK_SETTINGS['max_failures'])}")
        config_lines.append(f"checktolerance={settings.get('glider_check_tolerance', GLIDER_CHECK_SETTINGS['tolerance'])}")
        config_lines.append(f"checklatencysamples={settings.get('glider_check_latency_samples', GLIDER_CHECK_SETTINGS['latency_samples'])}")
        config_lines.append("")
        
        # 添加其他性能设置
        config_lines.append("# Performance Settings")
        config_lines.append(f"dialtimeout={settings.get('glider_dial_timeout', GLIDER_DEFAULTS['dial_timeout'])}")
        config_lines.append(f"relaytimeout={settings.get('glider_relay_timeout', GLIDER_DEFAULTS['relay_timeout'])}")
        config_lines.append(f"tcpbufsize={settings.get('glider_tcp_buf_size', GLIDER_DEFAULTS['tcp_buf_size'])}")
        config_lines.append(f"udpbufsize={settings.get('glider_udp_buf_size', GLIDER_DEFAULTS['udp_buf_size'])}")
        config_lines.append("")
        
        # 添加规则文件
        config_lines.append("# Rule Files")
        config_lines.append("rules-dir=rules.d")
        
        return "\n".join(config_lines)
    
    @staticmethod
    def generate_rule_files(site_proxies: Dict[str, List[Proxy]], client_config: dict) -> Dict[str, str]:
        """生成规则文件"""
        rule_files = {}
        settings = client_config.get('settings', {})
        
        # 生成默认规则文件（放在最前面，作为基础配置）
        default_rules = []
        
        # 添加默认转发器（使用所有代理）
        default_rules.append("# Default Forwarders")
        for proxies in site_proxies.values():
            for proxy in proxies:
                forward = proxy.to_glider_url()
                if forward:
                    default_rules.append(f"forward={forward}")
        
        # 使用lha策略（基于延迟的高可用）
        default_rules.append(f"strategy={settings.get('glider_strategy', GLIDER_DEFAULTS['strategy'])}")
        
        # 添加规则
        default_rules.append("\n# Rules")
        default_rules.append("domain=connectivitycheck.gstatic.com")  # Google连接检查
        
        rule_files["0_default.rule"] = "\n".join(default_rules)
        
        # 为每个站点生成规则文件（按字母顺序排序）
        for site in sorted(site_proxies.keys()):
            proxies = site_proxies[site]
            if not proxies:
                continue
                
            rule_lines = []
            group_name = site.replace(".", "_")
            
            # 添加转发器
            rule_lines.append("# Forwarders")
            for proxy in proxies:
                forward = proxy.to_glider_url()
                if forward:
                    rule_lines.append(f"forward={forward}")
            
            # 使用lha策略（基于延迟的高可用）
            rule_lines.append(f"strategy={settings.get('glider_strategy', GLIDER_DEFAULTS['strategy'])}")
            
            # 添加域名规则
            rule_lines.append("\n# Domain Rules")
            rule_lines.append(f"domain={site}")
            
            # 添加DNS服务器
            rule_lines.append("\n# DNS Settings")
            for server in client_config.get('dns', {}).get('servers', []):
                if isinstance(server, dict) and server.get('domains', []) == ["geosite:cn"]:
                    continue
                if isinstance(server, str):
                    rule_lines.append(f"dnsserver={server}:53")
                else:
                    rule_lines.append(f"dnsserver={server['address']}:{server.get('port', 53)}")
            
            # 使用数字前缀确保加载顺序
            rule_files[f"1_{group_name}.rule"] = "\n".join(rule_lines)
        
        return rule_files