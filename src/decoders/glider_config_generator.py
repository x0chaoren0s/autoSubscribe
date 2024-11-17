from pathlib import Path
from typing import List, Dict, Any
from src.models.proxy_v2 import ProxyParser
from src.decoders.glider_decoder import GliderDecoder

class GliderConfigGenerator:
    """生成Glider配置文件"""
    
    @staticmethod
    def generate(data_dir: str = "tests/data", output_file: str = "config/glider.conf") -> None:
        """从*_yes.txt文件生成glider.conf"""
        # 基础配置
        base_config = [
            "verbose=True",
            "listen=:7630",
            "strategy=lha",
            "check=http://www.msftconnecttest.com/connecttest.txt#expect=200",
            "checkinterval=30",
            ""  # 空行分隔
        ]
        
        # 收集所有可用的代理链接
        glider_links = []
        data_path = Path(data_dir)
        
        for file in data_path.glob("*_yes.txt"):
            with open(file, "r", encoding="utf-8") as f:
                links = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                
            for link in links:
                try:
                    # 解析为元信息
                    proxy_info = ProxyParser.parse(link)
                    # 转换为glider链接
                    glider_link = GliderDecoder.decode(proxy_info)
                    glider_links.append(glider_link)
                except Exception as e:
                    print(f"Warning: Failed to convert link: {link[:50]}...")
                    print(f"Error: {str(e)}")
        
        # 生成forward配置
        forward_config = [f"forward={link}" for link in glider_links]
        
        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入配置文件
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(base_config + forward_config))
            
        print(f"\nGlider config generated:")
        print(f"- Total proxies: {len(glider_links)}")
        print(f"- Config file: {output_path}")

if __name__ == "__main__":
    GliderConfigGenerator.generate() 