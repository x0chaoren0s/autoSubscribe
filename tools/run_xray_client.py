import asyncio
import json
import os
import signal
import sys
from pathlib import Path

import yaml

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.xray_config_generator import XrayConfigGenerator
from src.models.proxy import Proxy
from src.parsers.protocols.protocol_parser_factory import ProtocolParserFactory
from src.utils.logger import Logger

async def load_proxies(results_file: Path, logger) -> list:
    """从结果文件加载代理"""
    proxies = []
    if not results_file.exists():
        logger.error(f"Results file not found: {results_file}")
        return proxies
        
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        parser = ProtocolParserFactory.create_parser(line)
                        proxy = parser.parse(line)
                        if proxy:
                            proxies.append(proxy)
                    except Exception as e:
                        logger.error(f"Failed to parse proxy: {e}")
    except Exception as e:
        logger.error(f"Error reading file {results_file}: {e}")
    
    return proxies

async def main():
    # 初始化日志
    logger = Logger()
    ProtocolParserFactory.set_logger(logger)
    
    # 加载配置
    with open('config/client_config.yaml', 'r') as f:
        client_config = yaml.safe_load(f)
    
    # 读取所有站点的结果文件
    site_proxies = {}
    total_proxies = 0
    proxy_types = {}
    
    for site, results_file in client_config['proxy_results'].items():
        results_path = Path(results_file)
        proxies = await load_proxies(results_path, logger)
        
        if proxies:
            site_proxies[site] = proxies
            total_proxies += len(proxies)
            # 统计代理类型
            for proxy in proxies:
                proxy_types[proxy.proxy_type] = proxy_types.get(proxy.proxy_type, 0) + 1
            logger.info(f"Loaded {len(proxies)} proxies for {site}")
    
    if not site_proxies:
        logger.error("No valid proxies found")
        return
    
    # 显示代理类型统计
    logger.info("\nProxy types distribution:")
    for proxy_type, count in sorted(proxy_types.items()):
        logger.info(f"  {proxy_type.upper():<10}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
    logger.info(f"  {'TOTAL':<10}: {total_proxies:>3} proxies")
    
    # 生成Xray配置
    xray_config = XrayConfigGenerator.generate_client_config(
        site_proxies=site_proxies,
        client_config=client_config
    )
    
    # 保存配置文件
    config_file = Path('config/xray_client.json')
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(xray_config, f, indent=2, ensure_ascii=False)
    
    # 显示使用说明
    logger.info(f"\nGenerated Xray config: {config_file}")
    
    # 显示入站端口
    logger.info("\nAvailable inbound ports:")
    for inbound in client_config['inbounds']:
        if inbound['protocol'] == 'socks':
            auth_info = ""
            if inbound.get('settings', {}).get('auth') == 'password':
                auth_info = f" (auth: {inbound['settings']['accounts'][0]['user']})"
            logger.info(f"  SOCKS5 {inbound['listen']}:{inbound['port']}{auth_info}")
        elif inbound['protocol'] == 'http':
            logger.info(f"  HTTP   {inbound['listen']}:{inbound['port']}")
    
    # 显示路由规则
    logger.info("\nRouting rules (in priority order):")
    logger.info("  1. geosite:category-ads-all -> Block")
    for site in site_proxies:
        display_name = client_config['target_hosts'][site].get('display_name', site)
        logger.info(f"  2. {site:<15} -> {display_name} proxies ({len(site_proxies[site])} available)")
    logger.info("  3. geosite:cn          -> Direct connection")
    logger.info("  4. geoip:cn            -> Direct connection")
    logger.info("  5. Other traffic       -> All proxies combined")
    
    # 显示代理统计
    logger.info("\nProxy distribution:")
    for site in site_proxies:
        display_name = client_config['target_hosts'][site].get('display_name', site)
        proxy_types = {}
        for proxy in site_proxies[site]:
            proxy_types[proxy.proxy_type] = proxy_types.get(proxy.proxy_type, 0) + 1
        logger.info(f"\n  [{display_name}]:")
        for proxy_type, count in sorted(proxy_types.items()):
            logger.info(f"    {proxy_type.upper():<10}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
    
    # 显示启动命令
    logger.info(f"\nTo start Xray:")
    logger.info(f"  {client_config['settings']['xray_path']} -c {config_file}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1) 