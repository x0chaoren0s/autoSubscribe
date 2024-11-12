import pytest
import asyncio
from src.testers.glider_tester import GliderTester

@pytest.mark.asyncio
async def test_glider_tester_with_real_proxies(test_proxies, logger, config):
    """测试Glider测试器对真实代理的检测"""
    tester = GliderTester(logger=logger, config=config)
    test_target = "www.google.com"
    
    for proxy_type, proxies in test_proxies.items():
        logger.info(f"\nTesting {proxy_type.upper()} proxies:")
        working_count = 0
        
        for proxy in proxies:
            try:
                if await tester.test(proxy, test_target):
                    working_count += 1
                    logger.info(f"[+] Working: {proxy.server}:{proxy.port}")
                else:
                    logger.debug(f"[-] Failed: {proxy.server}:{proxy.port}")
            except Exception as e:
                logger.error(f"Error testing {proxy.server}:{proxy.port}: {str(e)}")
        
        if proxies:
            success_rate = working_count / len(proxies) * 100
            logger.info(f"\nSuccess rate for {proxy_type.upper()}: {success_rate:.1f}% ({working_count}/{len(proxies)})")
        else:
            logger.warning(f"No {proxy_type.upper()} proxies to test") 