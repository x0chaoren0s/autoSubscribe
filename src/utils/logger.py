import logging
import sys
from pathlib import Path
from datetime import datetime

class Logger:
    """日志管理器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志文件名（使用时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"autoSubscribe_{timestamp}.log"
        
        # 配置日志格式
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            '%(message)s'  # 控制台只显示消息内容
        )
        
        # 文件处理器（记录所有级别）
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台处理器（只显示INFO及以上级别，且格式更简洁）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        
        # 配置根日志记录器
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        # 移除所有已存在的处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        # 添加新的处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 记录启动信息
        self.info("AutoSubscribe Started")
        self.debug(f"Log file: {log_file}")
    
    def debug(self, msg: str):
        """调试信息（只写入文件）"""
        self.logger.debug(msg)
    
    def info(self, msg: str):
        """普通信息（同时显示在控制台）"""
        # 如果是进度条信息，直接显示
        if msg.startswith('\r['):
            sys.stdout.write(msg)
            sys.stdout.flush()
            self.logger.debug(msg.replace('\r', ''))
            return
            
        # 如果是成功找到代理的信息，只记录到日志文件
        if msg.startswith('[+] Found working proxy'):
            self.logger.debug(msg)
            return
            
        # 如果是统计信息，保持原样显示
        if msg.startswith('[*]') or msg.startswith('='):
            self.logger.info(msg)
            return
            
        # 如果是获取代理源的信息，显示
        if msg.startswith('[+] Found') and 'proxies from' in msg:
            self.logger.info(msg)
            return
            
        # 如果是代理类型统计，显示
        if any(proxy_type in msg for proxy_type in ['VLESS', 'VMESS', 'TROJAN', 'SS', 'TOTAL']):
            self.logger.info(msg)
            return
            
        # 如果是结果统计，显示
        if any(text in msg for text in ['Total tested', 'Working', 'Success rate', 'Working proxies by type']):
            self.logger.info(msg)
            return
            
        # 其他信息写入debug日志
        self.debug(msg)
    
    def warning(self, msg: str):
        """警告信息"""
        self.logger.warning(msg)
    
    def error(self, msg: str):
        """错误信息（错误信息也只在文件中详细记录）"""
        if msg.startswith('[!]'):
            # 显示错误标题
            self.logger.error(msg)
            return
            
        # 其他错误信息写入debug日志
        self.debug(msg)
    
    def section(self, title: str):
        """添加一个分节标题"""
        if title == "Results":
            # Results部分不需要分隔线
            self.info("")
            return
        
        # 其他部分使用分隔线
        self.info(f"\n=== {title} ===")

    def separator(self, title: str, width: int = 20):
        """添加一个分隔线"""
        # 计算需要的等号数量
        total_width = width
        title_width = len(title)
        left_width = (total_width - title_width) // 2
        right_width = total_width - title_width - left_width
        
        # 生成分隔线
        separator = "=" * left_width + title + "=" * right_width
        self.info(separator)