import pytest
from src.testers.base_tester import BaseTester
from src.testers.tcp_tester import TCPTester
from src.encoders.encoder import ProxyEncoder
from typing import Dict, Any, Optional

class DummyTester(BaseTester):
    """用于测试的虚拟测试器"""
    def get_tester_name(self) -> str:
        return "Dummy"
        
    async def test(self, proxy_info: Dict[str, Any], target_host: Optional[str] = None) -> bool:
        return True

@pytest.mark.asyncio
async def test_base_tester():
    """测试基础测试器"""
    # 使用虚拟测试器测试基类
    tester = DummyTester()
    assert tester.get_tester_name() == "Dummy"
    assert await tester.test({}, None) is True
    
    # 测试抽象方法
    with pytest.raises(TypeError):
        BaseTester()

@pytest.mark.asyncio
async def test_tcp_tester():
    """测试TCP测试器"""
    tester = TCPTester(timeout=1, retry_times=1)
    assert tester.get_tester_name() == "TCP"
    
    # 测试有效代理
    valid_link = "ss://YWVzLTEyOC1nY206dGVzdA@127.0.0.1:8388#Example"
    proxy_info = ProxyEncoder.encode(valid_link)
    result = await tester.test(proxy_info)
    assert isinstance(result, bool)
    
    # 测试无效代理
    invalid_link = "ss://YWVzLTEyOC1nY206dGVzdA@invalid.host:8388#Example"
    proxy_info = ProxyEncoder.encode(invalid_link)
    result = await tester.test(proxy_info)
    assert result is False

@pytest.mark.asyncio
async def test_tcp_tester_with_target():
    """测试TCP测试器（带目标主机）"""
    tester = TCPTester(timeout=1, retry_times=1)
    
    # 准备测试数据
    link = "ss://YWVzLTEyOC1nY206dGVzdA@127.0.0.1:8388#Example"
    proxy_info = ProxyEncoder.encode(link)
    
    # 测试不同的目标主机
    targets = [
        "www.google.com",
        "www.github.com",
        "invalid.host.name"
    ]
    
    for target in targets:
        result = await tester.test(proxy_info, target)
        assert isinstance(result, bool)

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 