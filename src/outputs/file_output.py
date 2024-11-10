import os
import shutil
from typing import List
from pathlib import Path
from datetime import datetime
from ..models.proxy import Proxy

class FileOutput:
    """文件输出处理器"""
    
    def __init__(self, logger=None, output_dir: str = "results", backup_dir: str = "results/backup", config: dict = None):
        """
        初始化文件输出处理器
        
        Args:
            logger: 日志记录器
            output_dir: 输出目录路径，默认为'results'
            backup_dir: 备份目录路径，默认为'results/backup'
            config: 配置字典
        """
        self.logger = logger
        self.config = config or {}
        self.output_dir = Path(output_dir)
        self.backup_dir = Path(backup_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def backup_results(self) -> None:
        """备份现有结果"""
        if not list(self.output_dir.glob("*.txt")):  # 如果没有结果文件，直接返回
            return
            
        # 创建备份目录（使用配置的时间戳格式）
        backup_format = self.config.get('output', {}).get('backup_format', "%Y%m%d_%H%M%S")
        timestamp = datetime.now().strftime(backup_format)
        backup_path = self.backup_dir / timestamp
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # 移动所有txt文件到备份目录
        for file in self.output_dir.glob("*.txt"):
            try:
                shutil.move(str(file), str(backup_path / file.name))
                if self.logger:
                    self.logger.debug(f"Backed up {file} to {backup_path / file.name}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error backing up {file}: {str(e)}")
    
    def save(self, target_host: str, proxies: List[Proxy], config: dict = None) -> None:
        """
        保存代理列表到对应的文件
        
        Args:
            target_host: 目标主机域名
            proxies: 可用的代理列表
            config: 配置字典，用于获取显示名称
        """
        if not proxies:  # 如果没有可用代理，不创建文件
            if self.logger:
                self.logger.debug(f"No proxies to save for {target_host}")
            return
        
        # 获取显示名称
        display_name = target_host
        if config and 'target_hosts' in config and target_host in config['target_hosts']:
            display_name = config['target_hosts'][target_host].get('display_name', target_host)
            
        output_file = self.output_dir / f"{target_host}.txt"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # 使用 with 语句确保文件正确关闭
            with output_file.open('w', encoding='utf-8') as f:
                # 写入文件头部信息
                f.write(f"# Available proxies for {display_name}\n")
                f.write(f"# Generated at: {current_time}\n")
                f.write(f"# Total: {len(proxies)}\n")
                f.write("#" + "=" * 50 + "\n\n")
                
                # 按代理类型分组写入
                by_type = self._group_by_type(proxies)
                for proxy_type, type_proxies in by_type.items():
                    if type_proxies:
                        f.write(f"\n# {proxy_type.upper()} Proxies:\n")
                        for proxy in type_proxies:
                            f.write(f"{proxy.raw_link}\n")
                        f.write("\n")
                
            if self.logger:
                self.logger.debug(f"Successfully saved {len(proxies)} proxies to {output_file}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error saving proxies for {display_name}: {str(e)}")
    
    def _group_by_type(self, proxies: List[Proxy]) -> dict:
        """
        将代理按类型分组
        
        Args:
            proxies: 代理列表
            
        Returns:
            dict: 按类型分组的代理字典
        """
        result = {}
        for proxy in proxies:
            if proxy.proxy_type not in result:
                result[proxy.proxy_type] = []
            result[proxy.proxy_type].append(proxy)
        
        # 按类型名称排序
        return dict(sorted(result.items()))
    
    def clear_results(self) -> None:
        """备份现有结果并清空结果目录"""
        self.backup_results()  # 先备份现有结果