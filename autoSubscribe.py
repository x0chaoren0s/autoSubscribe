#!/usr/bin/env python3

import asyncio
import argparse
import json
import sys
import time
import yaml
from pathlib import Path
from typing import List, Dict

from src.utils.logger import Logger
from src.utils.xray_config_generator import XrayConfigGenerator
from src.utils.glider_config_generator import GliderConfigGenerator
from src.models.proxy import Proxy
from src.parsers.line_parser import LineParser
from src.parsers.base64_parser import Base64Parser
from src.parsers.protocols.protocol_parser_factory import ProtocolParserFactory
from src.testers.tcp_tester import TCPTester
from src.testers.xray_tester import XrayTester
from src.testers.glider_tester import GliderTester
from src.testers.ssh_tester import SSHTester
from src.fetchers.http_fetcher import HttpFetcher
from src.outputs.file_output import FileOutput
from tqdm import tqdm

def format_time(seconds: float) -> str:
    """格式化时间显示"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        seconds = int(seconds % 60)
        return f"{minutes}m{seconds:02d}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h{minutes:02d}m"

async def filter_subscriptions(logger: Logger):
    """清洗订阅源的代理"""
    try:
        # 加载配置
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # 备份现有结果
        logger.info("\nBacking up previous results...")
        output = FileOutput(
            logger=logger,
            output_dir=config.get('output', {}).get('dir', 'results'),
            backup_dir=config.get('output', {}).get('backup', {}).get('dir', 'results/backup'),
            config=config
        )
        output.backup_results()
        
        # 获取代理
        logger.section("Fetching Proxies")
        all_proxies = []
        
        # 配置HTTP获取器
        fetcher_config = config.get('fetcher', {})
        http_fetcher = HttpFetcher(
            logger=logger,
            timeout=fetcher_config.get('timeout', 10),
            max_retries=fetcher_config.get('retry_times', 3)
        )
        
        # 获取所有订阅源的代理
        for url in config['subscription_urls']:
            try:
                content = await http_fetcher.fetch(url)
                proxies = await parse_subscription(content, logger)
                if proxies:
                    all_proxies.extend(proxies)
                    logger.info(f"[+] Found {len(proxies)} proxies from {url}")
            except Exception as e:
                logger.error(f"[-] Failed to fetch from {url}: {str(e)}")
        
        # 显示代理统计
        if not all_proxies:
            logger.error("No proxies found")
            return
            
        proxy_types = {}
        for proxy in all_proxies:
            proxy_types[proxy.proxy_type] = proxy_types.get(proxy.proxy_type, 0) + 1
        
        logger.info("\n[*] Proxy Statistics:")
        for proxy_type, count in sorted(proxy_types.items()):
            logger.info(f"    {proxy_type.upper():<10}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
        logger.info(f"    {'TOTAL':<10}: {len(all_proxies):>3} proxies\n")
        
        # 初始化站点代理字典
        site_proxies = {site: [] for site in config['target_hosts']}
        
        # 测试代理
        logger.section("Testing Proxies")
        
        # 获取测试器配置
        testers_config = config.get('testers', {})
        default_concurrent = testers_config.get('concurrent_tests', 5)
        default_timeout = testers_config.get('connect_timeout', 10)
        default_retry = testers_config.get('retry_times', 2)
        
        # 初始化测试器
        tcp_config = testers_config.get('tcp_tester', {})
        glider_config = testers_config.get('glider_tester', {})
        
        tcp_tester = TCPTester(
            logger=logger,
            timeout=tcp_config.get('connect_timeout', default_timeout),
            retry_times=tcp_config.get('retry_times', default_retry)
        ) if tcp_config.get('enabled', True) else None
        
        glider_tester = GliderTester(
            logger=logger,
            config={
                'glider': {
                    'timeout': glider_config.get('connect_timeout', default_timeout),
                    'retry_times': glider_config.get('retry_times', default_retry),
                    'check_url': glider_config.get('check_url'),
                    'check_expect': glider_config.get('check_expect'),
                    'check_interval': glider_config.get('check_interval'),
                    'check_timeout': glider_config.get('check_timeout'),
                    'max_failures': glider_config.get('max_failures')
                }
            }
        ) if glider_config.get('enabled', True) else None
        
        # 获取glider并发数
        concurrent_tests = glider_config.get('concurrent_tests', default_concurrent)
        
        # 创建信号量来限制并发
        semaphore = asyncio.Semaphore(concurrent_tests)
        
        # 创建异步测试函数
        async def test_proxy(proxy, pbar):
            async with semaphore:  # 使用信号量控制并发
                try:
                    # TCP连接测试
                    if tcp_tester and not await tcp_tester.test(proxy, None):
                        return
                    
                    # 对每个目标站点进行测试
                    for site in config['target_hosts']:
                        target_host = config['target_hosts'][site].get('host', site)
                        
                        # 使用glider进行测试
                        if glider_tester and await glider_tester.test(proxy, target_host):
                            site_proxies[site].append(proxy)
                            # 更新进度条的postfix
                            pbar.set_postfix_str(get_sites_status())
                            break
                    
                except Exception as e:
                    if logger:
                        logger.debug(f"Test failed for {proxy}: {str(e)}")
                finally:
                    pbar.update(1)  # 更新进度条
        
        # 创建一个函数来生成站点状态字符串
        def get_sites_status():
            status = []
            for site in config['target_hosts']:
                display_name = config['target_hosts'][site].get('display_name', site)
                working = len(site_proxies[site])
                status.append(f"{display_name}:{working}")
            return " ".join(status)
        
        # 使用tqdm创建进度条
        total_proxies = len(all_proxies)
        with tqdm(
            total=total_proxies,
            desc="Progress",
            unit="proxy",
            bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}",
            postfix=get_sites_status()
        ) as pbar:
            # 创建所有测试任务
            tasks = [test_proxy(proxy, pbar) for proxy in all_proxies]
            # 等待所有任务完成
            await asyncio.gather(*tasks)
        
        # 保存结果
        for site in site_proxies:
            if site_proxies[site]:
                output.save(site, site_proxies[site], config)
                logger.info(f"\nSaved {len(site_proxies[site])} working proxies for {site}")
            else:
                logger.warning(f"\nNo working proxies found for {site}")
        
    except Exception as e:
        logger.error(f"\nUnexpected error: {str(e)}")
        return

async def generate_xray_config(logger: Logger):
    """生成Xray配置文件"""
    # 加载配置
    with open('config/client_config.yaml', 'r') as f:
        client_config = yaml.safe_load(f)
    
    # 读取所有站点的结果文件
    site_proxies = {}
    ssh_proxies = {}  # 存储SSH代理
    total_proxies = 0
    proxy_types = {}
    error_stats = {
        'unsupported_methods': {},  # 不支持的加密方法
        'legacy_methods': {},       # 旧的加密方法
        'parse_errors': {},         # 解析错误
        'other_errors': {}          # 其他错误
    }
    
    for site, results_file in client_config['proxy_results'].items():
        results_path = Path(results_file)
        proxies = await load_proxies(results_path, logger)
        valid_proxies = []
        site_ssh_proxies = []
        
        # 验证每个代理的配置
        for proxy in proxies:
            try:
                if proxy.proxy_type == 'ssh':
                    site_ssh_proxies.append(proxy)
                    proxy_types['ssh'] = proxy_types.get('ssh', 0) + 1
                    total_proxies += 1
                    continue
                    
                # 验证Xray代理配置
                XrayConfigGenerator._generate_proxy_settings(proxy)
                XrayConfigGenerator._generate_stream_settings(proxy)
                valid_proxies.append(proxy)
                total_proxies += 1
                proxy_types[proxy.proxy_type] = proxy_types.get(proxy.proxy_type, 0) + 1
                
            except ValueError as e:
                error_msg = str(e)
                if "Legacy encryption method not supported" in error_msg:
                    method = error_msg.split(": ")[1]
                    error_stats['legacy_methods'][method] = error_stats['legacy_methods'].get(method, 0) + 1
                elif "Unknown encryption method" in error_msg:
                    method = error_msg.split(": ")[1]
                    error_stats['unsupported_methods'][method] = error_stats['unsupported_methods'].get(method, 0) + 1
                elif "Invalid shadowsocks link" in error_msg:
                    error_stats['parse_errors']['ss'] = error_stats['parse_errors'].get('ss', 0) + 1
                else:
                    error_stats['other_errors'][error_msg] = error_stats['other_errors'].get(error_msg, 0) + 1
                continue
            except Exception as e:
                error_msg = str(e)
                error_stats['other_errors'][error_msg] = error_stats['other_errors'].get(error_msg, 0) + 1
                continue
        
        if valid_proxies:
            site_proxies[site] = valid_proxies
            logger.info(f"Loaded {len(valid_proxies)} valid proxies for {site}")
            
        if site_ssh_proxies:
            ssh_proxies[site] = site_ssh_proxies
            logger.info(f"Loaded {len(site_ssh_proxies)} SSH proxies for {site}")
    
    if not site_proxies and not ssh_proxies:
        logger.error("No valid proxies found")
        return
    
    # 显示代理类型统计
    logger.info("\nProxy types distribution:")
    for proxy_type, count in sorted(proxy_types.items()):
        logger.info(f"  {proxy_type.upper():<10}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
    logger.info(f"  {'TOTAL':<10}: {total_proxies:>3} proxies")
    
    # 显示错误统计
    if any(error_stats.values()):
        logger.info("\nError statistics:")
        
        if error_stats['legacy_methods']:
            logger.info("\n  Legacy encryption methods (not supported):")
            for method, count in sorted(error_stats['legacy_methods'].items()):
                logger.info(f"    {method:<20}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
        
        if error_stats['unsupported_methods']:
            logger.info("\n  Unknown encryption methods:")
            for method, count in sorted(error_stats['unsupported_methods'].items()):
                logger.info(f"    {method:<20}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
        
        if error_stats['parse_errors']:
            logger.info("\n  Parse errors:")
            for error_type, count in sorted(error_stats['parse_errors'].items()):
                logger.info(f"    {error_type:<20}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
        
        if error_stats['other_errors']:
            logger.info("\n  Other errors:")
            for error_msg, count in sorted(error_stats['other_errors'].items()):
                logger.info(f"    {error_msg:<50}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
    
    # 生成Xray配置
    try:
        xray_config = XrayConfigGenerator.generate_client_config(
            site_proxies=site_proxies,
            client_config=client_config
        )
        
        xray_config_file = Path('config/xray_client.json')
        with open(xray_config_file, 'w', encoding='utf-8') as f:
            json.dump(xray_config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\nXray config file saved to: {xray_config_file}")
    except Exception as e:
        logger.error(f"Failed to generate Xray config: {str(e)}")
    
    # 生成Glider配置
    try:
        glider_config = GliderConfigGenerator.generate_client_config(
            site_proxies=site_proxies,
            client_config=client_config
        )
        
        glider_config_file = Path('config/glider.conf')
        with open(glider_config_file, 'w', encoding='utf-8') as f:
            f.write(glider_config)
        
        logger.info(f"Glider config file saved to: {glider_config_file}")
        logger.info(f"To start glider, run: glider -config {glider_config_file}")
    except Exception as e:
        logger.error(f"Failed to generate Glider config: {str(e)}")
        return
    
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
    for site in site_proxies:
        display_name = client_config['target_hosts'][site].get('display_name', site)
        logger.info(f"  1. {site:<15} -> {display_name} proxies ({len(site_proxies[site])} available)")
    logger.info("  2. geosite:category-ads-all -> Block")
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

async def generate_glider_config(logger: Logger):
    """生成Glider配置文件"""
    # 加载配置
    with open('config/client_config.yaml', 'r') as f:
        client_config = yaml.safe_load(f)
    
    # 读取所有站点的结果文件
    site_proxies = {}
    ssh_proxies = {}  # 存储SSH代理
    total_proxies = 0
    proxy_types = {}
    error_stats = {
        'unsupported_methods': {},  # 不支持的加密方法
        'legacy_methods': {},       # 旧的加密方法
        'parse_errors': {},         # 解析错误
        'other_errors': {}          # 其他错误
    }
    
    for site, results_file in client_config['proxy_results'].items():
        results_path = Path(results_file)
        proxies = await load_proxies(results_path, logger)
        valid_proxies = []
        site_ssh_proxies = []
        
        # 验证每个代理的配置
        for proxy in proxies:
            try:
                if proxy.proxy_type == 'ssh':
                    site_ssh_proxies.append(proxy)
                    proxy_types['ssh'] = proxy_types.get('ssh', 0) + 1
                    total_proxies += 1
                    continue
                    
                # 验证代理配置
                glider_url = proxy.to_glider_url()
                if glider_url:
                    valid_proxies.append(proxy)
                    total_proxies += 1
                    proxy_types[proxy.proxy_type] = proxy_types.get(proxy.proxy_type, 0) + 1
                else:
                    error_stats['parse_errors'][proxy.proxy_type] = error_stats['parse_errors'].get(proxy.proxy_type, 0) + 1
                
            except ValueError as e:
                error_msg = str(e)
                if "Legacy encryption method not supported" in error_msg:
                    method = error_msg.split(": ")[1]
                    error_stats['legacy_methods'][method] = error_stats['legacy_methods'].get(method, 0) + 1
                elif "Unknown encryption method" in error_msg:
                    method = error_msg.split(": ")[1]
                    error_stats['unsupported_methods'][method] = error_stats['unsupported_methods'].get(method, 0) + 1
                else:
                    error_stats['other_errors'][error_msg] = error_stats['other_errors'].get(error_msg, 0) + 1
                continue
            except Exception as e:
                error_msg = str(e)
                error_stats['other_errors'][error_msg] = error_stats['other_errors'].get(error_msg, 0) + 1
                continue
        
        if valid_proxies:
            site_proxies[site] = valid_proxies
            logger.info(f"Loaded {len(valid_proxies)} valid proxies for {site}")
            
        if site_ssh_proxies:
            ssh_proxies[site] = site_ssh_proxies
            logger.info(f"Loaded {len(site_ssh_proxies)} SSH proxies for {site}")
    
    if not site_proxies and not ssh_proxies:
        logger.error("No valid proxies found")
        return
    
    # 显示代理类��统计
    logger.info("\nProxy types distribution:")
    for proxy_type, count in sorted(proxy_types.items()):
        logger.info(f"  {proxy_type.upper():<10}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
    logger.info(f"  {'TOTAL':<10}: {total_proxies:>3} proxies")
    
    # 显示错误统计
    if any(error_stats.values()):
        logger.info("\nError statistics:")
        
        if error_stats['legacy_methods']:
            logger.info("\n  Legacy encryption methods (not supported):")
            for method, count in sorted(error_stats['legacy_methods'].items()):
                logger.info(f"    {method:<20}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
        
        if error_stats['unsupported_methods']:
            logger.info("\n  Unknown encryption methods:")
            for method, count in sorted(error_stats['unsupported_methods'].items()):
                logger.info(f"    {method:<20}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
        
        if error_stats['parse_errors']:
            logger.info("\n  Parse errors:")
            for error_type, count in sorted(error_stats['parse_errors'].items()):
                logger.info(f"    {error_type:<20}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
        
        if error_stats['other_errors']:
            logger.info("\n  Other errors:")
            for error_msg, count in sorted(error_stats['other_errors'].items()):
                logger.info(f"    {error_msg:<50}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
    
    # 生成Glider配置
    try:
        # 生成主配置文件
        glider_config = GliderConfigGenerator.generate_client_config(
            site_proxies=site_proxies,
            client_config=client_config
        )
        
        # 创建规则文件目录
        rules_dir = Path('config/rules.d')
        rules_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成规则文件
        rule_files = GliderConfigGenerator.generate_rule_files(
            site_proxies=site_proxies,
            client_config=client_config
        )
        
        # 保存规则文件
        for filename, content in rule_files.items():
            rule_file = rules_dir / filename
            with open(rule_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.debug(f"Rule file saved to: {rule_file}")
        
        # 保存主配置文件
        glider_config_file = Path('config/glider.conf')
        with open(glider_config_file, 'w', encoding='utf-8') as f:
            f.write(glider_config)
        
        logger.info(f"\nGlider config file saved to: {glider_config_file}")
        logger.info(f"To start glider, run: glider -config {glider_config_file}")
        
    except Exception as e:
        logger.error(f"Failed to generate Glider config: {str(e)}")
        return
    
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
    for site in site_proxies:
        display_name = client_config['target_hosts'][site].get('display_name', site)
        logger.info(f"  1. {site:<15} -> {display_name} proxies ({len(site_proxies[site])} available)")
    logger.info("  2. geosite:category-ads-all -> Block")
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

async def load_proxies(results_file: Path, logger) -> List[Proxy]:
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
                            # 清理代理设置
                            proxy.clean_settings()
                            proxies.append(proxy)
                    except Exception as e:
                        logger.error(f"Failed to parse line: {str(e)}")
    except Exception as e:
        logger.error(f"Error reading results file: {str(e)}")
        
    return proxies

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='AutoSubscribe - 自动订阅、测试和管理代理服务器的工具')
    parser.add_argument('--filter_subscriptions', action='store_true', help='清洗订阅源的代理')
    parser.add_argument('--generate_xray_config', action='store_true', help='生成Xray配置文件')
    parser.add_argument('--generate_glider_config', action='store_true', help='生成Glider配置文件')
    args = parser.parse_args()
    
    # 初始化日志
    logger = Logger()
    ProtocolParserFactory.set_logger(logger)
    
    try:
        if args.filter_subscriptions:
            asyncio.run(filter_subscriptions(logger))
        elif args.generate_xray_config:
            asyncio.run(generate_xray_config(logger))
        elif args.generate_glider_config:
            asyncio.run(generate_glider_config(logger))
        else:
            parser.print_help()
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\nUnexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 