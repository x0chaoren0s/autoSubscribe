import pytest
import yaml
from pathlib import Path
from typing import Dict, List
from src.models.proxy import Proxy
from src.utils.logger import Logger
from src.parsers.line_parser import LineParser

@pytest.fixture
def logger():
    """提供日志记录器"""
    return Logger()

@pytest.fixture
def config():
    """提供测试配置"""
    with open('config/config.yaml', 'r') as f:
        return yaml.safe_load(f)

@pytest.fixture
def test_links() -> Dict[str, List[str]]:
    """加载测试链接"""
    links = {
        'vmess': [],
        'vless': [],
        'ss': [],
        'trojan': [],
        'ssh': []
    }
    data_dir = Path('tests/data')
    
    # 加载各类型的测试链接
    for file in data_dir.glob('*_links.txt'):
        proxy_type = file.stem.split('_')[0]
        if proxy_type in links:
            with open(file, 'r', encoding='utf-8') as f:
                links[proxy_type] = [
                    line.strip() for line in f
                    if line.strip() and not line.startswith('#')
                ]
    
    return links

@pytest.fixture
def test_proxies(test_links, logger) -> Dict[str, List[Proxy]]:
    """将测试链接转换为代理对象"""
    proxies = {
        'vmess': [],
        'vless': [],
        'ss': [],
        'trojan': [],
        'ssh': []
    }
    parser = LineParser(logger=logger)
    
    for proxy_type, links in test_links.items():
        for link in links:
            try:
                proxy = parser.parse(link)
                if proxy:
                    proxies[proxy_type].append(proxy)
            except Exception as e:
                logger.error(f"Failed to parse {proxy_type} link: {str(e)}")
    
    return proxies