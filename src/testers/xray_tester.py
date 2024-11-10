import asyncio
import json
import os
import re
import socket
import tempfile
from pathlib import Path
from typing import Dict, List

import aiohttp

from .base_tester import BaseTester
from ..models.proxy import Proxy

class XrayTester(BaseTester):
    """使用Xray测试代理可用性"""
    
    def __init__(self, config: dict, logger=None, xray_path: str = None, timeout: int = 10):
        """
        初始化XrayTester
        
        Args:
            config: 配置字典
            logger: 日志记录器
            xray_path: xray可执行文件路径
            timeout: 默认超时时间
        """
        self.config = config
        self.logger = logger
        self.xray_path = xray_path or config.get('xray', {}).get('path', '/usr/local/bin/xray')
        self.timeout = timeout
        
    async def test(self, proxy: Proxy, target_host: str) -> bool:
        """测试代理是否可用"""
        process = None
        config_path = None
        try:
            # 获取空闲端口
            self.local_port = self._get_free_port()
            
            # 创建临时配置文件
            config = self._generate_config(proxy, target_host)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(config, temp_file)
                config_path = temp_file.name
            
            # 启动xray进程
            process = await asyncio.create_subprocess_exec(
                self.xray_path,
                '-config', config_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            if process.returncode is not None:
                self.logger.error(f"Xray process failed to start: {process.returncode}")
                return False
            
            self.logger.debug(f"Started Xray process (PID: {process.pid}) for {proxy.server}:{proxy.port}")
            
            # 等待xray启动并尝试连接
            for i in range(3):  # 最多尝试3次
                await asyncio.sleep(2)  # 每次等待2秒
                try:
                    result = await self._test_connection(target_host)
                    if result:
                        return True
                except Exception as e:
                    self.logger.debug(f"Connection attempt {i+1} failed: {str(e)}")
            
            return False
                
        except Exception as e:
            self.logger.error(f"Error testing proxy {proxy.server}:{proxy.port}: {str(e)}")
            return False
            
        finally:
            # 清理资源
            if process:
                try:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Process termination timeout, killing PID: {process.pid}")
                        process.kill()
                        await process.wait()
                    self.logger.debug(f"Terminated Xray process (PID: {process.pid})")
                except ProcessLookupError:
                    self.logger.debug("Process already terminated")
                except Exception as e:
                    self.logger.error(f"Error cleaning up Xray process: {str(e)}")
            
            if config_path:
                try:
                    os.unlink(config_path)
                except Exception as e:
                    self.logger.error(f"Error removing config file: {str(e)}")
    
    def _generate_config(self, proxy: Proxy, target_host: str) -> Dict:
        """生成Xray配置"""
        config = {
            "log": {
                "loglevel": "warning",
                "access": "none"  # 禁用访问日志
            },
            "dns": {  # 添加DNS配置
                "servers": [
                    "1.1.1.1",  # Cloudflare DNS
                    "8.8.8.8",  # Google DNS
                    {
                        "address": "114.114.114.114",  # 国内DNS
                        "port": 53,
                        "domains": ["geosite:cn"]  # 国内域名
                    }
                ],
                "queryStrategy": "UseIPv4"  # 优先使用IPv4
            },
            "inbounds": [{
                "tag": "socks",
                "port": self.local_port,
                "protocol": "socks",
                "settings": {
                    "auth": "noauth",
                    "udp": True,
                    "ip": "127.0.0.1"  # 只监听本地
                },
                "sniffing": {  # 启用流量探测
                    "enabled": True,
                    "destOverride": ["http", "tls", "quic"],
                    "metadataOnly": False  # 完整的域名嗅探
                }
            }],
            "outbounds": [{
                "tag": "proxy",
                "protocol": proxy.proxy_type,
                "settings": self._generate_proxy_settings(proxy),
                "streamSettings": self._generate_stream_settings(proxy)
            }, {
                "tag": "direct",
                "protocol": "freedom",
                "settings": {
                    "domainStrategy": "UseIPv4"  # 优先使用IPv4
                }
            }],
            "routing": {
                "domainStrategy": "IPOnDemand",
                "rules": [
                    # 优先级0：强制目标站点走代理
                    {
                        "type": "field",
                        "domain": [target_host],
                        "outboundTag": "proxy"
                    },
                    # 优先级1：其他流量直连
                    {
                        "type": "field",
                        "network": "tcp,udp",
                        "outboundTag": "direct"
                    }
                ]
            }
        }
        
        self.logger.debug(f"Generated config for {proxy.server}:{proxy.port}:")
        self.logger.debug(json.dumps(config, indent=2))
        return config
    
    def _generate_proxy_settings(self, proxy: Proxy) -> Dict:
        """根据代理类型生成相应的设置"""
        if proxy.proxy_type == "vmess":
            return {
                "vnext": [{
                    "address": proxy.server,
                    "port": proxy.port,
                    "users": [{
                        "id": proxy.settings['id'],
                        "alterId": int(proxy.settings.get('aid', 0))
                    }]
                }]
            }
        elif proxy.proxy_type == "vless":
            return {
                "vnext": [{
                    "address": proxy.server,
                    "port": proxy.port,
                    "users": [{
                        "id": proxy.settings['uuid'],
                        "encryption": proxy.settings.get('encryption', 'none')
                    }]
                }]
            }
        elif proxy.proxy_type == "trojan":
            return {
                "servers": [{
                    "address": proxy.server,
                    "port": proxy.port,
                    "password": proxy.settings['password']
                }]
            }
        elif proxy.proxy_type == "ss":
            return {
                "servers": [{
                    "address": proxy.server,
                    "port": proxy.port,
                    "method": proxy.settings['method'],
                    "password": proxy.settings['password']
                }]
            }
        else:
            raise ValueError(f"Unsupported proxy type: {proxy.proxy_type}")
    
    def _generate_stream_settings(self, proxy: Proxy) -> Dict:
        """生成传输层设置"""
        transport_type = proxy.settings.get('type', 'tcp')
        settings = {
            "network": transport_type,
            "security": proxy.settings.get('security', 'none')
        }
        
        # TLS设置
        if proxy.settings.get('tls') == 'tls' or proxy.settings.get('security') == 'tls':
            settings["security"] = "tls"
            settings["tlsSettings"] = {
                "serverName": proxy.settings.get('sni', proxy.server),
                "allowInsecure": True,  # 允许不安全的证书
                "fingerprint": proxy.settings.get('fp', 'chrome'),  # 使用Chrome指纹
                "alpn": ["h2", "http/1.1"]  # 支持的协议
            }
        
        # WebSocket设置
        if transport_type == "ws":
            settings["wsSettings"] = {
                "path": proxy.settings.get('path', '/'),
                "headers": {
                    "Host": proxy.settings.get('host', proxy.server)
                }
            }
            # 如果没有设置security，但有host，也启用TLS
            if settings["security"] == "none" and proxy.settings.get('host'):
                settings["security"] = "tls"
                settings["tlsSettings"] = {
                    "serverName": proxy.settings['host'],
                    "allowInsecure": True,
                    "fingerprint": "chrome",
                    "alpn": ["h2", "http/1.1"]
                }
        elif transport_type == "tcp":
            settings["tcpSettings"] = {
                "header": {
                    "type": "none"
                }
            }
        
        self.logger.debug(f"Stream settings for {proxy.server}:{proxy.port}:")
        self.logger.debug(json.dumps(settings, indent=2))
        return settings
    
    async def _test_connection(self, target_host: str) -> bool:
        """测试到目标主机的连接"""
        host_config = self.config['target_hosts'][target_host]
        test_url = host_config['test_url']
        timeout = host_config.get('timeout', self.timeout)
        headers = host_config.get('headers', {})
        retry_times = host_config.get('retry_times', 2)
        
        # 获取状态码配置
        status_codes = host_config.get('status_codes', {
            'success': [200, 503, 500, 502, 504],  # 只保留这些状态码表示成功
            'retry': [429, 520, 521, 522]
        })
        
        # 尝试HTTPS和HTTP
        urls = [
            test_url,  # 首先尝试配置的URL
            test_url.replace('http://', 'https://', 1) if test_url.startswith('http://') else test_url,  # 尝试HTTPS
            test_url.replace('https://', 'http://', 1) if test_url.startswith('https://') else test_url,  # 尝试HTTP
        ]
        urls = list(set(urls))  # 去重
        
        proxy_url = f"socks5://127.0.0.1:{self.local_port}"
        
        # 记录所有错误，如果都失败了，返回最详细的错误信息
        errors = []
        
        for url in urls:
            self.logger.debug(f"Testing connection to {url}")
            for attempt in range(retry_times):
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                        async with session.get(
                            url,
                            proxy=proxy_url,
                            ssl=False,  # 禁用SSL验证
                            headers=headers,
                            allow_redirects=True  # 允许重定向
                        ) as response:
                            self.logger.debug(f"Attempt {attempt + 1}: Got response {response.status} from {url}")
                            
                            # 检查状态码
                            if response.status in status_codes['success']:
                                # 如果是200，还需要检查内容
                                if response.status == 200 and host_config.get('expected_pattern'):
                                    try:
                                        content = await response.text(encoding='utf-8', errors='ignore')
                                        pattern = host_config['expected_pattern']
                                        if re.search(pattern, content):
                                            self.logger.debug(f"Content pattern matched for {url}")
                                            return True
                                        else:
                                            errors.append(f"Content pattern not found in {url}: {pattern}")
                                    except UnicodeDecodeError as e:
                                        self.logger.debug(f"Failed to decode response content from {url}: {str(e)}")
                                        # 即使解码失败，如果状态码是200，我们也认为代理是可用的
                                        return True
                                else:
                                    # 其他成功状态码直接返回True
                                    self.logger.debug(f"Got success status code {response.status} from {url}")
                                    return True
                            elif response.status in status_codes['retry']:
                                # 需要重试的状态码
                                errors.append(f"Got retry status code {response.status} from {url}")
                                continue
                            else:
                                errors.append(f"Got unexpected status code {response.status} from {url}")
                                
                except asyncio.TimeoutError:
                    errors.append(f"Attempt {attempt + 1} timed out after {timeout}s for {url}")
                except aiohttp.ClientError as e:
                    errors.append(f"Attempt {attempt + 1} failed with client error for {url}: {str(e)}")
                except Exception as e:
                    errors.append(f"Attempt {attempt + 1} failed with unexpected error for {url}: {str(e)}")
                
                # 如果不是最后一次尝试，等待一下再重试
                if attempt < retry_times - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    self.logger.debug(f"Waiting {wait_time}s before retry {url}")
                    await asyncio.sleep(wait_time)
        
        # 如果所有尝试都失败了，记录最详细的错误信息
        if errors:
            self.logger.debug("All attempts failed:")
            for error in errors:
                self.logger.debug(f"  - {error}")
        
        return False
    
    def _get_free_port(self) -> int:
        """获取一个可用的端口号"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port