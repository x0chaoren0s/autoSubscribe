from typing import List
from .base_parser import BaseParser

class LineParser(BaseParser):
    """行解析器 - 用于解析按行分隔的订阅内容"""
    
    def parse(self, content: str) -> List[str]:
        """解析按行分隔的内容为代理链接列表"""
        try:
            lines = []
            for line in content.splitlines():
                line = line.strip()
                
                # 1. 跳过空行和纯注释行
                if not line or line.startswith('#'):
                    continue
                
                # 2. 如果有空格，在第一个空格处截断
                if ' ' in line:
                    line = line.split(None, 1)[0]
                
                # 3. 如果没有空格但有多个#，只保留到第二个#之前的部分
                elif line.count('#') > 1:
                    protocol_part = line.split('://', 1)
                    if len(protocol_part) == 2:
                        protocol, rest = protocol_part
                        # 找到第二个#的位置
                        first_hash = rest.find('#')
                        if first_hash != -1:
                            second_hash = rest.find('#', first_hash + 1)
                            if second_hash != -1:
                                line = f"{protocol}://{rest[:second_hash]}"
                
                # 4. 验证是否是有效的代理链接
                if "://" not in line:
                    continue
                
                lines.append(line)
                    
            return lines
            
        except Exception as e:
            raise ValueError(f"Invalid content format: {str(e)}")