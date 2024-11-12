import pytest
import asyncio
from src.testers.tcp_tester import TCPTester

@pytest.mark.asyncio
async def test_tcp_tester_with_real_proxies(test_proxies, logger, config):
    """测试TCP测试器对真实代理的检测"""
    tester = TCPTester(logger=logger, config=config)
    
    for proxy_type, proxies in test_proxies.items():
        logger.info(f"\nTesting {proxy_type.upper()} proxies:")
        working_count = 0
        
        for proxy in proxies:
            try:
                if await tester.test(proxy, None):
                    working_count += 1
                    logger.info(f"[+] TCP connection successful: {proxy.server}:{proxy.port}")
                else:
                    logger.debug(f"[-] TCP connection failed: {proxy.server}:{proxy.port}")
            except Exception as e:
                logger.error(f"Error testing {proxy.server}:{proxy.port}: {str(e)}")
        
        if proxies:
            success_rate = working_count / len(proxies) * 100
            logger.info(f"\nTCP success rate for {proxy_type.upper()}: {success_rate:.1f}% ({working_count}/{len(proxies)})")
        else:
            logger.warning(f"No {proxy_type.upper()} proxies to test")

@pytest.mark.asyncio
async def test_tcp_tester_connection_timeout(test_proxies, logger, config):
    """测试TCP测试器的超时处理"""
    # 使用较短的超时时间
    config['testers']['tcp_tester'] = {
        'connect_timeout': 1,  # 1秒超时
        'retry_times': 1
    }
    
    tester = TCPTester(logger=logger, config=config)
    
    for proxy_type, proxies in test_proxies.items():
        for proxy in proxies:
            # 修改端口为不可用端口以触发超时
            original_port = proxy.port
            proxy.port = 1  # 通常不可用的端口
            
            try:
                result = await tester.test(proxy, None)
                assert not result, f"Expected timeout for {proxy.server}:{proxy.port}"
            except Exception as e:
                logger.debug(f"Expected timeout error: {str(e)}")
            finally:
                proxy.port = original_port  # 恢复原始端口 