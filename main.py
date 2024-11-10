# 标准库导入
import asyncio
import time
import sys

# 第三方库导入
import yaml

# 自定义组件导入
from src.utils.logger import Logger

# 解析器相关导入
from src.parsers.line_parser import LineParser
from src.parsers.base64_parser import Base64Parser
from src.parsers.protocols.protocol_parser_factory import ProtocolParserFactory

# 测试器相关导入
from src.testers.tcp_tester import TCPTester
from src.testers.xray_tester import XrayTester

# 其他组件导入
from src.fetchers.http_fetcher import HttpFetcher
from src.outputs.file_output import FileOutput

def get_proxy_signature(proxy):
    """获取代理的特征签名"""
    return f"{proxy.proxy_type}:{proxy.server}:{proxy.port}"

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

def get_progress_message(completed_count, total_proxies, results, hosts, config, start_time=None):
    """生成进度消息"""
    progress = completed_count / total_proxies
    bar_width = 30
    filled = int(bar_width * progress)
    bar = '█' * filled + '░' * (bar_width - filled)
    percent = progress * 100
    working_counts = {host: len(results[host]) for host in hosts}
    
    # 计算ETA和处理速率
    eta_str = ""
    rate_str = ""
    elapsed_str = ""
    if start_time and completed_count > 0:
        elapsed = time.time() - start_time
        rate = completed_count / elapsed  # 每秒处理的代理数
        remaining = (total_proxies - completed_count) / rate if rate > 0 else 0
        
        # 格式化处理速率
        if rate >= 1:
            rate_str = f"{rate:.1f}p/s"  # 每秒处理多个代理
        else:
            # 转换为每个代理需要多少秒
            seconds_per_proxy = 1 / rate
            rate_str = f"{seconds_per_proxy:.1f}s/p"  # 每个代理需要多少秒
        
        # 格式化已用时间和剩余时间
        elapsed_str = format_time(elapsed)
        eta_str = format_time(remaining)
    
    # 简化进度显示
    progress_str = f"{completed_count}/{total_proxies}"
    
    # 使用配置的显示名称
    working_str = ", ".join(
        f"{config['target_hosts'][host].get('display_name', host.split('.')[0])}: {count}" 
        for host, count in working_counts.items()
    )
    
    return f"\r[{bar}] {percent:>4.1f}% | {progress_str} | {rate_str} | Used: {elapsed_str} | ETA: {eta_str} | {working_str}"

async def test_proxies(proxies, hosts, tester, tcp_tester, logger, semaphore, config):
    """并发测试所有代理"""
    total_proxies = len(proxies)
    results = {host: [] for host in hosts}
    
    # 记录已测试过的代理特征及其结果
    tested_signatures = {host: {} for host in hosts}
    
    # 记录已完成测试的代理数量和开始时间
    completed_count = 0
    last_progress_msg = ""
    start_time = time.time()  # 记录开始时间
    
    async def test_with_progress(i, proxy):
        nonlocal completed_count, last_progress_msg
        async with semaphore:
            proxy_sig = get_proxy_signature(proxy)
            
            # 首先进行TCP测试
            if not await tcp_tester.test(proxy):
                completed_count += 1
                logger.debug(f"TCP test failed for {proxy_sig}")
                
                # 更新进度显示
                progress_msg = get_progress_message(completed_count, total_proxies, results, hosts, config, start_time)
                if progress_msg != last_progress_msg:
                    logger.info(progress_msg)
                    last_progress_msg = progress_msg
                return
            
            logger.debug(f"TCP test passed for {proxy_sig}")
            
            # TCP测试通过后继续原有的测试流程
            for host in hosts:
                if proxy_sig in tested_signatures[host]:
                    success, first_proxy = tested_signatures[host][proxy_sig]
                    if success:
                        logger.debug(f"Skipping {proxy_sig} for {host} (similar proxy already working)")
                        continue
                
                try:
                    if await tester.test(proxy, host):
                        tested_signatures[host][proxy_sig] = (True, proxy)
                        results[host].append(proxy)
                        logger.debug(f"[+] Found working proxy for {host}: {proxy.proxy_type} - {proxy.server}:{proxy.port}")
                    else:
                        tested_signatures[host][proxy_sig] = (False, None)
                        logger.debug(f"[-] Failed proxy for {host}: {proxy.proxy_type} - {proxy.server}:{proxy.port}")
                except Exception as e:
                    tested_signatures[host][proxy_sig] = (False, None)
                    logger.debug(f"[!] Error testing proxy for {host}: {str(e)}")
            
            # 更新完成数量和显示进度
            completed_count += 1
            progress_msg = get_progress_message(completed_count, total_proxies, results, hosts, config, start_time)
            if progress_msg != last_progress_msg:
                logger.info(progress_msg)
                last_progress_msg = progress_msg
            
            # 每100个代理或进度变化超过5%时显示一次统计信息
            if completed_count % 100 == 0 or completed_count == total_proxies or (completed_count > 0 and completed_count % int(total_proxies * 0.05) == 0):
                logger.info("\n[*] Current Statistics:")
                for host in hosts:
                    display_name = config['target_hosts'][host].get('display_name', host)
                    success_rate = len(results[host])/completed_count*100 if completed_count > 0 else 0
                    logger.info(f"    {display_name:<10}: {len(results[host]):>4} working ({success_rate:>5.1f}%)")
                logger.info("")  # 空行
    
    # 创建并发任务
    tasks = []
    for i, proxy in enumerate(proxies):
        task = test_with_progress(i, proxy)
        tasks.append(task)
    
    # 等待所有任务完成
    await asyncio.gather(*tasks)
    
    return results

async def main():
    # 记录开始时间
    start_time = time.time()
    
    # 初始化日志
    logger = Logger()
    
    # 加载配置
    logger.section("Configuration")
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # 初始化组件
    logger.section("Initialization")
    fetcher = HttpFetcher(
        logger=logger,
        timeout=config.get('fetcher', {}).get('timeout', 30),
        max_retries=config.get('fetcher', {}).get('max_retries', 3),
        proxy=config.get('fetcher', {}).get('proxy')
    )
    ProtocolParserFactory.set_logger(logger)
    parsers = [LineParser(logger=logger), Base64Parser(logger=logger)]
    tester = XrayTester(config, logger=logger)
    tcp_tester = TCPTester(
        logger=logger,
        timeout=config.get('tcp_tester', {}).get('timeout', 2),
        retry_times=config.get('tcp_tester', {}).get('retry_times', 2)
    )
    output = FileOutput(
        logger=logger,
        output_dir=config.get('output', {}).get('dir', 'results'),
        backup_dir=config.get('output', {}).get('backup_dir', 'results/backup')
    )
    
    try:
        # 清理旧的结果
        logger.info("\nBacking up previous results...")
        output.clear_results()  # ���里会自动备份果
        
        # 获取所有代理
        logger.section("Fetching Proxies")
        all_proxies = []
        for url in config['subscription_urls']:
            try:
                content = await fetcher.fetch(url)
                parser = next(p for p in parsers if p.can_parse(content))
                proxies = parser.parse(content)
                all_proxies.extend(proxies)
                logger.info(f"[+] Found {len(proxies)} proxies from {url}")
            except Exception as e:
                logger.error(f"[!] Error processing {url}: {str(e)}")
        
        # 按类型统计代理数量
        proxy_stats = {}
        for proxy in all_proxies:
            proxy_stats[proxy.proxy_type] = proxy_stats.get(proxy.proxy_type, 0) + 1
        
        logger.info("\n[*] Proxy Statistics:")
        for proxy_type, count in sorted(proxy_stats.items()):
            logger.info(f"    {proxy_type.upper():<10}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
        logger.info(f"    {'TOTAL':<10}: {len(all_proxies):>3} {'proxy' if len(all_proxies) == 1 else 'proxies'}")
        
        # 测试所有代理
        logger.section("Testing Proxies")
        hosts = list(config['target_hosts'].keys())
        concurrent_tests = config.get('xray', {}).get('concurrent_tests', 3)
        semaphore = asyncio.Semaphore(concurrent_tests)
        
        results = await test_proxies(
            all_proxies, 
            hosts, 
            tester, 
            tcp_tester, 
            logger, 
            semaphore,
            config
        )
        
        # 保存并显示结果
        logger.section("Results")
        logger.info(f"Total tested : {len(all_proxies):>4} proxies")
        
        # 计算总的成功率
        total_working = sum(len(valid_proxies) for valid_proxies in results.values())
        total_success_rate = total_working / (len(all_proxies) * len(hosts)) * 100 if all_proxies and hosts else 0
        logger.info(f"Total success rate: {total_success_rate:>6.1f}%")
        
        # 显示每个站点的统计
        for host, valid_proxies in results.items():
            # 获取显示名称
            display_name = config['target_hosts'][host].get('display_name', host)
            
            # 保存结果
            output.save(host, valid_proxies, config)
            
            # 显示分隔线和统计
            logger.separator(display_name)
            logger.info(f"    Working     : {len(valid_proxies):>4} proxies")
            success_rate = len(valid_proxies)/len(all_proxies)*100 if all_proxies else 0
            logger.info(f"    Success rate: {success_rate:>6.1f}%")
            
            # 显示可用代理的类型统计
            valid_stats = {}
            for proxy in valid_proxies:
                valid_stats[proxy.proxy_type] = valid_stats.get(proxy.proxy_type, 0) + 1
            if valid_stats:
                logger.info(f"    Working proxies by type:")
                for proxy_type, count in sorted(valid_stats.items()):
                    logger.info(f"      {proxy_type.upper():<10}: {count:>3} {'proxy' if count == 1 else 'proxies'}")
        
        # 显示总耗时
        total_time = time.time() - start_time
        logger.info(f"\nTotal time: {format_time(total_time)}")
        logger.info(f"Average speed: {len(all_proxies)/total_time:.1f} proxies/s")
        
        logger.section("Complete")
    
    finally:
        # 清理资源
        await fetcher.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)