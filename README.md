# AutoSubscribe

自动订阅、测试和管理代理服务器的工具。

## 功能特点

- 自动获取和解析订阅源
- 支持多种代理协议
- 自动测试代理可用性
- 自动生成配置文件
- 支持站点专用代理分组
- 支持自动备份
- 暂时仅支持生成Glider配置


## 使用方法

### 1. 配置文件设置

编辑 `config/config.yaml` 和 `config/client_config.yaml`：
- 设置订阅源
- 配置目标站点
- 设置测试参数
- 配置入站端口

### 2. 代理清洗

```bash
python autoSubscribe.py --filter_subscriptions
```

这将：
- 获取所有订阅源的代理
- 进行TCP连接测试
- 对每个站点进行可用性测试
- 保存测试结果到results目录

### 3. 生成代理配置

生成Glider配置：
```bash
python autoSubscribe.py --generate_glider_config
```

启动Glider：
```bash
glider -config config/glider.conf
```

这将：
- 加载已测试的代理
- 生成相应的配置文件
- 显示入站端口和路由规则
- 提供启动命令

## 路由规则

优先级从高到低：
1. 目标站点 -> 专用代理（每个站点使用其专用代理组）
2. 其他流量 -> 所有代理负载均衡（自动选择延迟最低的代理）

## 注意事项

- Glider提供更好的负载均衡功能，建议优先使用Glider配置
- Glider支持的负载均衡策略：
  - rr: 轮询（Round Robin）
  - ha: 高可用（High Availability）
  - lha: 基于延迟的高可用（Latency based High Availability）
  - dh: 目标地址哈希（Destination Hashing）