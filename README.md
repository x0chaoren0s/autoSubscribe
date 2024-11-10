# AutoSubscribe

自动订阅、测试和管理代理服务器的工具。

## 功能特点

- 支持多种代理协议（VMess、VLESS、Trojan、Shadowsocks）
- 支持多个订阅源
- 支持TCP和Xray双重测试
- 支持多站点专用代理筛选
- 支持结果自动备份
- 支持自定义配置

## 安装要求

- Python 3.8+
- Xray-core

### Python依赖

```bash
pip install -r requirements.txt
```

### Xray安装

```bash
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
```

## 使用方法

### 1. 配置文件设置

编辑 `config/config.yaml` 和 `config/client_config.yaml`：
- 设置订阅源
- 配置目标站点
- 设置测试参数
- 配置入站端口

### 2. 代理清洗

```bash
python main.py
```

这将：
- 获取所有订阅源的代理
- 进行TCP连接测试
- 对每个站点进行可用性测试
- 保存测试结果到results目录

### 3. 启动Xray客户端

```bash
python tools/run_xray_client.py
```

这将：
- 加载已测试的代理
- 生成Xray配置
- 提供多个入站端口
- 自动进行负载均衡

## 配置文件说明

### config/config.yaml

主配置文件，包含：
- 订阅源列表
- 测试参数设置
- 目标站点配置
- 输出设置

### config/client_config.yaml

客户端配置文件，包含：
- 代理结果文件位置
- Xray入站设置（支持多个）
- DNS设置
- 路由规则配置

## 路由规则

优先级从高到低：
1. 广告域名 -> 阻止
2. 目标站点 -> 专用代理
3. 中国大陆域名 -> 直连
4. 中国大陆IP -> 直连
5. 其他流量 -> 所有代理负载均衡

## 目录结构

```
autoSubscribe/
├── config/                 # 配置文件目录
├── logs/                  # 日志文件目录
├── results/               # 代理结果目录
├── src/                   # 源代码目录
└── tools/                 # 工具脚本目录
```

## 注意事项

1. 首次运行前请确保配置文件正确
2. 建议定期清理备份目录
3. 可以通过修改配置文件调整并发数和超时时间
4. 日志文件会自动按日期归档
5. 每次运行会自动备份之前的结果

## 故障排除

1. 如果无法获取订阅源，检查fetcher配置中的代理设置
2. 如果测试速度太慢，可以增加concurrent_tests的值
3. 如果出现连接超时，可以调整timeout参数
4. 如果需要调试，可以查看logs目录下的日志文件

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 更新日志

### v1.0.0
- 初始版本发布
- 支持多协议
- 支持多站点测试
- 支持自动备份