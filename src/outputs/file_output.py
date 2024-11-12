import os
import shutil
import gzip
from typing import List, Dict
from pathlib import Path
from datetime import datetime
from ..models.proxy import Proxy
from ..utils.string_cleaner import StringCleaner

class FileOutput:
    """文件输出处理器"""
    
    def __init__(self, logger=None, output_dir: str = "results", config: Dict = None):
        """
        初始化文件输出处理器
        
        Args:
            logger: 日志记录器
            output_dir: 输出目录路径，默认为'results'
            config: 配置字典，包含以下结构：
                {
                    'output': {
                        'dir': str,           # 输出目录
                        'backup': {
                            'enabled': bool,  # 是否启用备份
                            'dir': str,       # 备份目录
                            'keep': int,      # 保留备份数量
                            'compress': bool  # 是否压缩备份
                        }
                    }
                }
        """
        self.logger = logger
        self.config = config or {}
        
        # 获取输出配置
        output_config = self.config.get('output', {})
        self.output_dir = Path(output_config.get('dir', output_dir))
        
        # 获取备份配置
        backup_config = output_config.get('backup', {})
        self.backup_enabled = backup_config.get('enabled', True)
        self.backup_dir = Path(backup_config.get('dir', 'results/backup'))
        self.backup_keep = backup_config.get('keep', 10)
        self.backup_compress = backup_config.get('compress', False)
        
        # 创建必要的目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.backup_enabled:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def backup_results(self) -> None:
        """备份现有结果"""
        if not self.backup_enabled:
            return
            
        if not list(self.output_dir.glob("*.txt")):  # 如果没有结果文件，直接返回
            return
            
        # 创建备份目录（使用时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / timestamp
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # 复制所有结果文件到备份目录
        for file in self.output_dir.glob("*.txt"):
            if self.backup_compress:
                # 使用gzip压缩
                backup_file = backup_path / f"{file.stem}.txt.gz"
                with open(file, 'rb') as f_in:
                    with gzip.open(backup_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # 直接复制
                shutil.copy2(file, backup_path)
            
        # 同时备份配置文件
        config_files = [
            Path('config/xray_client.json'),
            Path('config/glider.conf'),
            Path('config/rules.d')
        ]
        for config_file in config_files:
            if config_file.exists():
                if config_file.is_dir():
                    shutil.copytree(config_file, backup_path / config_file.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(config_file, backup_path)
            
        if self.logger:
            self.logger.debug(f"Results backed up to: {backup_path}")
        
        # 清理旧备份
        self._cleanup_old_backups()
    
    def _cleanup_old_backups(self) -> None:
        """清理旧的备份"""
        if not self.backup_keep:
            return
            
        # 获取所有备份目录
        backups = sorted([d for d in self.backup_dir.iterdir() if d.is_dir()])
        
        # 如果超过保留数量，删除最旧的备份
        while len(backups) > self.backup_keep:
            oldest = backups.pop(0)
            try:
                shutil.rmtree(oldest)
                if self.logger:
                    self.logger.debug(f"Removed old backup: {oldest}")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to remove old backup {oldest}: {str(e)}")
    
    def save(self, site: str, proxies: List[Proxy], config: dict = None) -> None:
        """
        保存代理到文件
        
        Args:
            site: 站点名称
            proxies: 代理列表
            config: 配置字典（可选）
        """
        config = config or self.config
        if not config:
            if self.logger:
                self.logger.error("No configuration provided")
            return
            
        # 获取输出文件路径
        output_file = self.output_dir / f"{site}.txt"
        
        try:
            # 按类型分组代理
            proxy_groups = self._group_by_type(proxies)
            
            # 获取站点显示名称
            display_name = config.get('target_hosts', {}).get(site, {}).get('display_name', site)
            
            # 写入文件
            with open(output_file, 'w', encoding='utf-8') as f:
                # 写入头部注释
                f.write(f"# {display_name} Proxies\n")
                f.write(f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total: {len(proxies)} proxies\n\n")
                
                # 按类型写入代理
                for proxy_type, type_proxies in sorted(proxy_groups.items()):
                    f.write(f"# {proxy_type.upper()}: {len(type_proxies)} proxies\n")
                    for proxy in type_proxies:
                        # 在保存前清理代理设置
                        proxy.clean_settings()
                        # 保存原始链接
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
        
        # 删除所有结果文件
        for file in self.output_dir.glob("*.txt"):
            try:
                file.unlink()
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error deleting file {file}: {str(e)}")
                    
        # 删除现有配置文件
        config_files = [
            Path('config/xray_client.json'),
            Path('config/glider.conf'),
            Path('config/rules.d')
        ]
        for config_file in config_files:
            try:
                if config_file.exists():
                    if config_file.is_dir():
                        shutil.rmtree(config_file)
                    else:
                        config_file.unlink()
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error deleting config file {config_file}: {str(e)}")