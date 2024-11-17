#!/usr/bin/env python3

import asyncio
import argparse
import json
import sys
import time
import yaml
from pathlib import Path
from typing import List, Dict, Any

from src.utils.logger import Logger
from src.utils.xray_config_generator import XrayConfigGenerator
from src.utils.glider_config_generator import GliderConfigGenerator
from src.encoders.encoder import ProxyEncoder
from src.parsers.line_parser import LineParser
from src.parsers.base64_parser import Base64Parser
from src.testers.tcp_tester import TCPTester
from src.testers.xray_tester import XrayTester
from src.testers.glider_tester import GliderTester
from src.testers.ssh_tester import SSHTester
from src.fetchers.http_fetcher import HttpFetcher
from src.outputs.file_output import FileOutput
from tqdm import tqdm
from src.validators.proxy_validator import ProxyValidator
from src.decoders.glider_decoder import GliderDecoder

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

async def parse_subscription(content: str, logger: Logger) -> List[str]:
    """解析订阅内容并返回代理链接列表"""
    try:
        # 尝试Base64解码
        parser = Base64Parser()
        lines = parser.parse(content)
                
    except Exception as e:
        # 如果Base64解析失败，尝试直接按行解析
        logger.debug(f"Base64 parsing failed, trying line by line: {str(e)}")
        line_parser = LineParser()
        lines = line_parser.parse(content)
    
    return lines

async def filter_subscriptions(logger: Logger):
    """清洗订阅源的代理"""
    try:
        # 加载配置
        with open('config/proxies_filter.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # 备份现有结果
        logger.info("\nBacking up previous results...")
        output = FileOutput(
            logger=logger,
            output_dir=config['output']['dir'],
            backup_dir=config['output']['backup']['dir'],
            config=config
        )
        output.backup_results()
        
        # 获取代理
        logger.section("Fetching Proxies")
        
        # 使用集合存储所有代理链接，自动去重
        all_proxy_links = set()
        
        # 配置HTTP获取器
        fetcher_config = config['subscription']['fetcher']
        http_fetcher = HttpFetcher(
            logger=logger,
            connect_timeout=fetcher_config['timeout'],
            max_retries=fetcher_config['retry_times'],
            proxy=fetcher_config.get('proxy')
        )
        
        # 获取所有订阅源的代理链接
        for url in config['subscription']['urls']:
            try:
                content = await http_fetcher.fetch(url)
                proxy_links = await parse_subscription(content, logger)
                if proxy_links:
                    original_count = len(all_proxy_links)
                    all_proxy_links.update(proxy_links)
                    new_count = len(all_proxy_links)
                    added_count = new_count - original_count
                    logger.info(f"[+] Found {len(proxy_links)} proxies from {url} ({added_count} new)")
            except Exception as e:
                logger.error(f"[-] Failed to fetch from {url}: {str(e)}")
        
        if not all_proxy_links:
            logger.error("No proxies found")
            return
            
        # 将代理链接转换为元信息
        logger.info(f"\nConverting {len(all_proxy_links)} unique proxy links to metadata")
        all_proxies = []
        for link in all_proxy_links:
            try:
                proxy_info = ProxyEncoder.encode(link)
                if proxy_info:
                    all_proxies.append(proxy_info)
            except Exception as e:
                logger.debug(f"Failed to encode link: {str(e)}")
        
        # 验证代理配置
        logger.section("Validating Proxies")
        validator = ProxyValidator()
        valid_proxies = []
        invalid_count = 0
        
        for proxy in all_proxies:
            valid, reason = validator.validate(proxy)
            if valid:
                valid_proxies.append(proxy)
            else:
                invalid_count += 1
                logger.debug(f"Invalid proxy configuration: {reason}")
        
        if not valid_proxies:
            logger.error("No valid proxies found")
            return
            
        # 显示代理统计
        proxy_types = {}
        for proxy in valid_proxies:
            proxy_type = proxy["proxy_protocol"].value
            proxy_types[proxy_type] = proxy_types.get(proxy_type, 0) + 1
        
        logger.info("\n[*] Proxy Statistics:")
        for proxy_type, count in sorted(proxy_types.items()):
            logger.info(f"    {proxy_type.upper():<10}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
        logger.info(f"    {'INVALID':<10}: {invalid_count:>3} proxies")
        logger.info(f"    {'TOTAL':<10}: {len(valid_proxies):>3} valid proxies\n")
        
        # 测试代理
        logger.section("Testing Proxies")
        
        # 初始化测试器
        testers_config = config['testers']
        
        # TCP测试器 - 仅测试代理服务器是否在线
        tcp_config = testers_config['tcp_tester']
        tcp_tester = TCPTester(
            logger=logger,
            connect_timeout=tcp_config['connect_timeout'],
            retry_times=tcp_config['retry_times']
        ) if tcp_config['enabled'] else None
        
        # Xray测试器 - 测试代理连通性
        xray_config = testers_config['xray_tester']
        xray_tester = XrayTester(
            logger=logger,
            timeout=xray_config['connect_timeout'],
            retry_times=xray_config['retry_times'],
            xray_path=xray_config['xray_path']
        ) if xray_config['enabled'] else None
        
        # Glider测试器 - 测试代理连通性
        glider_config = testers_config['glider_tester']
        glider_tester = GliderTester(
            logger=logger,
            config=glider_config
        ) if glider_config['enabled'] else None
        
        # 创建信号量来限制并发
        concurrent_tests = testers_config['basic']['concurrent_tests']
        semaphore = asyncio.Semaphore(concurrent_tests)
        
        # 初始化站点代理字典
        site_proxies = {site: [] for site in config['target_hosts'].keys()}
        
        # 进度条
        progress = tqdm(
            total=len(valid_proxies),
            desc="Progress",
            dynamic_ncols=True,  # 启用动态宽度
            leave=True,  # 完成后保留进度条
            smoothing=0.1,  # 平滑进度更新
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]'
        )
        working_count = 0
        
        # 测试函数
        async def test_proxy(proxy):
            nonlocal working_count
            async with semaphore:
                # 1. 首先进行TCP连接测试（检查代理服务器是否在线）
                if tcp_tester and not await tcp_tester.test(proxy):
                    progress.update(1)
                    progress.set_postfix_str(f"working:{working_count}")
                    return False
                
                # 2. 然后使用配置的测试器测试目标站点的连通性
                test_results = []
                
                # 使用Xray测试
                if xray_tester:
                    for site, site_config in config['target_hosts'].items():
                        if await xray_tester.test(proxy, site_config):
                            test_results.append(site)
                            break
                
                # 使用Glider测试
                if glider_tester:
                    for site, site_config in config['target_hosts'].items():
                        if await glider_tester.test(proxy, site_config):
                            test_results.append(site)
                            break
                
                # 更新站点代理字典
                for site in test_results:
                    site_proxies[site].append(proxy)
                    working_count += 1
                
                progress.update(1)
                progress.set_postfix_str(f"working:{working_count}")
                return bool(test_results)
        
        # 并发测试所有代理
        tasks = [test_proxy(proxy) for proxy in valid_proxies]
        await asyncio.gather(*tasks)
        
        progress.close()
        
        # 检查结果
        total_site_proxies = sum(len(proxies) for proxies in site_proxies.values())
        if total_site_proxies == 0:
            logger.error("\nNo working proxies found for any target site")
            return
            
        # 显示结果
        logger.info("\nWorking proxies by site:")
        for site, proxies in site_proxies.items():
            if proxies:
                logger.info(f"  {site}: {len(proxies)} proxies")
        
        # 保存结果
        output = FileOutput(
            logger=logger,
            output_dir=config['output']['dir'],
            backup_dir=config['output']['backup']['dir'],
            config=config
        )
        
        for site, proxies in site_proxies.items():
            if proxies:
                output.save(site, proxies)
        
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
    for site, proxies in site_proxies.items():
        site_config = client_config['target_hosts'].get(site, {})
        display_name = site_config.get('display_name', site)
        logger.info(f"  1. {site:<15} -> {display_name} proxies ({len(proxies)} available)")
    logger.info("  2. geosite:category-ads-all -> Block")
    logger.info("  3. geosite:cn          -> Direct connection")
    logger.info("  4. geoip:cn            -> Direct connection")
    logger.info("  5. Other traffic       -> All proxies combined")
    
    # 显示代理统计
    logger.info("\nProxy distribution:")
    for site, proxies in site_proxies.items():
        site_config = client_config['target_hosts'].get(site, {})
        display_name = site_config.get('display_name', site)
        proxy_types = {}
        for proxy in proxies:
            proxy_type = proxy["proxy_protocol"].value
            proxy_types[proxy_type] = proxy_types.get(proxy_type, 0) + 1
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
    total_proxies = 0
    proxy_types = {}
    error_stats = {
        'decode_errors': {},  # 解码错误
        'other_errors': {}    # 其他错误
    }
    
    for site, results_file in client_config['proxy_results'].items():
        results_path = Path(results_file)
        if not results_path.exists():
            logger.warning(f"Results file not found: {results_file}")
            continue
            
        # 读取代理链接
        with open(results_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
        valid_proxies = []
        # 验证每个代理的配置
        for line in lines:
            try:
                # 解析为元信息
                proxy_info = ProxyEncoder.encode(line)
                # 尝试转换为glider链接
                glider_link = GliderDecoder.decode(proxy_info)
                if glider_link:
                    valid_proxies.append(proxy_info)
                    total_proxies += 1
                    proxy_type = proxy_info["proxy_protocol"].value
                    proxy_types[proxy_type] = proxy_types.get(proxy_type, 0) + 1
                    
            except Exception as e:
                error_msg = str(e)
                if "Failed to decode" in error_msg:
                    proxy_type = error_msg.split(" ")[3]  # 提取协议类型
                    error_stats['decode_errors'][proxy_type] = error_stats['decode_errors'].get(proxy_type, 0) + 1
                else:
                    error_stats['other_errors'][error_msg] = error_stats['other_errors'].get(error_msg, 0) + 1
                continue
        
        if valid_proxies:
            site_proxies[site] = valid_proxies
            logger.info(f"Loaded {len(valid_proxies)} valid proxies for {site}")
                
    if not site_proxies:
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
        
        if error_stats['decode_errors']:
            logger.info("\n  Decode errors:")
            for proxy_type, count in sorted(error_stats['decode_errors'].items()):
                logger.info(f"    {proxy_type:<20}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
        
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
    for site, proxies in site_proxies.items():
        site_config = client_config['target_hosts'].get(site, {})
        display_name = site_config.get('display_name', site)
        logger.info(f"  1. {site:<15} -> {display_name} proxies ({len(proxies)} available)")
    logger.info("  2. geosite:category-ads-all -> Block")
    logger.info("  3. geosite:cn          -> Direct connection")
    logger.info("  4. geoip:cn            -> Direct connection")
    logger.info("  5. Other traffic       -> All proxies combined")
    
    # 显示代理统计
    logger.info("\nProxy distribution:")
    for site, proxies in site_proxies.items():
        site_config = client_config['target_hosts'].get(site, {})
        display_name = site_config.get('display_name', site)
        proxy_types = {}
        for proxy in proxies:
            proxy_type = proxy["proxy_protocol"].value
            proxy_types[proxy_type] = proxy_types.get(proxy_type, 0) + 1
        logger.info(f"\n  [{display_name}]:")
        for proxy_type, count in sorted(proxy_types.items()):
            logger.info(f"    {proxy_type.upper():<10}: {count:>3} {'proxy' if count == 1 else 'proxies'}")

async def load_proxies(results_file: Path, logger) -> List[Dict[str, Any]]:
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
                        proxy_info = ProxyEncoder.encode(line)
                        if proxy_info:
                            proxies.append(proxy_info)
                    except Exception as e:
                        logger.error(f"Failed to encode line: {str(e)}")
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