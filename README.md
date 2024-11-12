# AutoSubscribe

自动订阅、测试和管理代理服务器的工具。

## 功能特点

- 自动获取和解析订阅源
- 支持多种代理协议
- 自动测试代理可用性
- 自动生成配置文件
- 支持站点专用代理分组
- 支持自动备份
- 支持Xray和Glider两种客户端

## 支持的协议和加密方法

### Shadowsocks
支持的加密方法：
- aes-128-gcm
- aes-256-gcm
- chacha20-poly1305
- chacha20-ietf-poly1305
- xchacha20-poly1305
- 2022-blake3-aes-128-gcm
- 2022-blake3-aes-256-gcm
- 2022-blake3-chacha20-poly1305

注意：不再支持以下旧的加密方法：
- aes-128-ctr
- aes-192-ctr
- aes-256-ctr
- aes-128-cfb
- aes-192-cfb
- aes-256-cfb
- rc4-md5
- chacha20
- chacha20-ietf

### VMess
- 支持 TCP、WebSocket、HTTP、gRPC 传输
- 支持 TLS、Reality 安全传输
- 支持 alterID 设置

### VLESS
- 支持 TCP、WebSocket、HTTP、gRPC 传输
- 支持 TLS、Reality 安全传输
- 支持 XTLS 流控

### Trojan
- 支持 TCP、WebSocket 传输
- 支持 TLS 安全传输

### SSH
- 支持密码认证
- 支持密钥认证
- 支持自定义SSH选项
- 链接格式：
  ```
  ssh://[username[:password]@]hostname[:port][?key=private_key_path&key_password=key_password&ssh_Option1=Value1&ssh_Option2=Value2]
  ```
- 示例：
  ```
  ssh://user:pass@example.com:22
  ssh://example.com?key=/path/to/key
  ssh://user@example.com?ssh_ServerAliveInterval=60
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
python autoSubscribe.py --filter_subscriptions
```

这将：
- 获取所有订阅源的代理
- 进行TCP连接测试
- 对每个站点进行可用性测试
- 保存测试结果到results目录

### 3. 生成代理配置

生成Xray配置：
```bash
python autoSubscribe.py --generate_xray_config
```

启动Xray：
```bash
xray -c config/xray_client.json
```

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
2. 广告域名 -> 阻止
3. 中国大陆域名 -> 直连
4. 中国大陆IP -> 直连
5. 其他流量 -> 所有代理负载均衡（自动选择延迟最低的代理）

## 注意事项

- SSH代理不会包含在Xray配置中，需要使用SSH客户端单独连接
- 建议对SSH代理使用密钥认证以提高安全性
- SSH代理支持的选项可以在链接中通过ssh_前缀设置
- Glider提供更好的负载均衡功能，建议优先使用Glider配置
- Glider支持的负载均衡策略：
  - rr: 轮询（Round Robin）
  - ha: 高可用（High Availability）
  - lha: 基于延迟的高可用（Latency based High Availability）
  - dh: 目标地址哈希（Destination Hashing）