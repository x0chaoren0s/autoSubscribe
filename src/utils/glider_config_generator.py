from typing import Dict, List, Any
from pathlib import Path
from src.decoders.glider_decoder import GliderDecoder

class GliderConfigGenerator:
    """Glider配置生成器"""
    
    @staticmethod
    def generate_client_config(site_proxies: Dict[str, List[Dict[str, Any]]], client_config: Dict) -> str:
        """生成Glider客户端配置"""
        config_lines = []
        
        # 基础配置
        glider_config = client_config.get('glider', {})
        config_lines.extend([
            "verbose=True",
            f"listen={glider_config.get('listen', ':7630')}",
            f"strategy={glider_config.get('strategy', 'lha')}",
            f"check={glider_config.get('check_url', 'http://www.msftconnecttest.com/connecttest.txt#expect=200')}",
            f"checkinterval={glider_config.get('check_interval', 30)}",
            f"rules-dir={glider_config.get('rules_dir', 'rules.d')}",
            "\n"
        ])

        # 收集所有代理链接
        all_forwards = set()
        for proxies in site_proxies.values():
            for proxy in proxies:
                try:
                    glider_link = GliderDecoder.decode(proxy)
                    all_forwards.add(f"forward={glider_link}")
                except Exception:
                    continue
                    
        # 添加所有代理集合
        if all_forwards:
            config_lines.extend([
                "# All proxies combined",
                *all_forwards,
                ""
            ])
        
        return "\n".join(config_lines)

    @staticmethod
    def _get_domain_rule(site: str) -> str:
        """获取站点的域名规则"""
        domain_map = {
            "google": "google.com",
            "github": "github.com",
            "pixiv": "pixiv.net",
            "nhentai": "nhentai.net",
            "pornhub": "pornhub.com",
            "xnxx": "xnxx.com"
        }
        return domain_map.get(site, f"{site}.com")

    @staticmethod
    def generate_rule_files(site_proxies: Dict[str, List[Dict[str, Any]]], client_config: Dict) -> Dict[str, str]:
        """生成Glider规则文件"""
        rule_files = {}
        
        # 生成站点规则
        for site, proxies in site_proxies.items():
            if not proxies:
                continue
                
            # 获取站点配置
            site_config = client_config['target_hosts'].get(site, {})
            
            # 生成规则内容
            rule_lines = [
                f"# Rules for {site}",
                f"domain={GliderConfigGenerator._get_domain_rule(site)}",
                f"strategy=lha",
                f"check={site_config['check_url']}",
                f"checkinterval=30",
                ""  # 空行分隔
            ]
            
            # 添加代理链接
            forward_lines = []
            for proxy in proxies:
                try:
                    glider_link = GliderDecoder.decode(proxy)
                    forward_lines.append(f"forward={glider_link}")
                except Exception:
                    continue
                    
            if forward_lines:
                rule_lines.extend(forward_lines)
            
            rule_files[f"{site}.rule"] = "\n".join(rule_lines)
        
        return rule_files