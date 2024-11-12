"""常量定义"""

# 默认端口
DEFAULT_PORTS = {
    'ss': 8388,
    'vmess': 443,
    'vless': 443,
    'trojan': 443,
    'ssh': 22,
    'http': 80,
    'https': 443,
    'socks5': 1080
}

# 默认值
DEFAULT_VALUES = {
    'port': 443,
    'path': '/',
    'host': '',
    'type': 'tcp',
    'security': 'none',
    'flow': '',
    'sni': '',
    'alpn': '',
    'fp': '',
    'pbk': '',
    'sid': '',
    'spx': ''
}

# 超时设置（秒）
DEFAULT_TIMEOUTS = {
    'connect': 5,
    'read': 10,
    'write': 10,
    'test': 10,
    'dns': 3
}

# 重试次数
DEFAULT_RETRIES = 2

# 支持的协议
SUPPORTED_PROTOCOLS = ['ss', 'vmess', 'vless', 'trojan', 'ssh']

# SS加密方法映射（glider支持的格式）
SUPPORTED_SS_METHODS = {
    'aes-128-gcm': 'AEAD_AES_128_GCM',
    'aes-256-gcm': 'AEAD_AES_256_GCM',
    'chacha20-poly1305': 'AEAD_CHACHA20_POLY1305',
    'chacha20-ietf-poly1305': 'AEAD_CHACHA20_POLY1305',
    'xchacha20-poly1305': 'AEAD_XCHACHA20_POLY1305',
    'xchacha20-ietf-poly1305': 'AEAD_XCHACHA20_POLY1305'
}

# 旧的SS加密方法（不再支持）
LEGACY_SS_METHODS = {
    'aes-128-ctr': 'AES-128-CTR',
    'aes-192-ctr': 'AES-192-CTR',
    'aes-256-ctr': 'AES-256-CTR',
    'aes-128-cfb': 'AES-128-CFB',
    'aes-192-cfb': 'AES-192-CFB',
    'aes-256-cfb': 'AES-256-CFB',
    'rc4-md5': 'RC4-MD5',
    'chacha20': 'CHACHA20',
    'chacha20-ietf': 'CHACHA20-IETF'
}

# VMess加密方法映射
VMESS_METHODS = {
    'auto': 'aes-128-gcm',
    'none': 'zero',
    'zero': 'zero',
    'aes-128-gcm': 'aes-128-gcm',
    'chacha20-poly1305': 'chacha20-poly1305'
}

# VMess传输协议
VMESS_NETWORKS = {
    'tcp': 'tcp',
    'ws': 'ws',
    'http': 'http',
    'h2': 'h2',
    'grpc': 'grpc',
    'quic': 'quic'
}

# TLS设置
TLS_SETTINGS = {
    'tls': True,
    'xtls': True,
    'reality': True,
    'none': False
}

# WebSocket设置
WS_SETTINGS = {
    'path': '/',
    'host': '',
    'max_early_data': 0,
    'early_data_header': 'Sec-WebSocket-Protocol'
}

# HTTP头部
HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive'
}

# TLS指纹
TLS_FINGERPRINTS = {
    'chrome': 'chrome',
    'firefox': 'firefox',
    'safari': 'safari',
    'ios': 'ios',
    'android': 'android',
    'edge': 'edge',
    'random': 'random'
}

# ALPN协议
ALPN_PROTOCOLS = ['h2', 'http/1.1']

# 需要清理的字段
CLEAN_FIELDS = [
    'path',
    'host',
    'sni',
    'alpn',
    'fp',
    'pbk',
    'sid',
    'spx'
]

# 特殊字符
SPECIAL_CHARS = {
    'path': ['<', '>', '"', '\'', ' '],
    'host': ['<', '>', '"', '\'', ' '],
    'sni': ['<', '>', '"', '\'', ' ', ','],
    'alpn': ['<', '>', '"', '\'', ' ']
}

# 参数验证相关
INVALID_CHARS = {
    'url': ['#', ' '],
    'host': [',', ';', '#', ' '],
    'path': ['#', ' '],
    'param': [',', ';', '#', ' ']
}

# 参数长度限制
MAX_LENGTHS = {
    'host': 255,
    'path': 2048,
    'param': 2048
}

# 参数格式验证
PARAM_PATTERNS = {
    'host': r'^[-a-zA-Z0-9._*]+$',
    'path': r'^[-a-zA-Z0-9._/]+$',
    'uuid': r'^[0-9a-f-]+$'
}

# Glider默认设置
GLIDER_DEFAULTS = {
    'strategy': 'lha',                # 默认使用基于延迟的高可用策略
    'check_interval': 30,             # 检查间隔（秒）
    'check_timeout': 10,              # 检查超时（秒）
    'max_failures': 3,                # 最大失败次数
    'check_tolerance': 100,           # 延迟容差（毫秒）
    'check_latency_samples': 10,      # 延迟采样数
    'check_url': 'http://www.msftconnecttest.com/connecttest.txt',  # 检查URL
    'check_expect': '200',            # 期望的响应
    'dial_timeout': 3,                # 连接超时（秒）
    'relay_timeout': 0,               # 转发超时（秒，0表示不限制）
    'tcp_buf_size': 32768,           # TCP缓冲区大小（字节）
    'udp_buf_size': 2048,            # UDP缓冲区大小（字节）
    'dns_timeout': 3,                 # DNS查询超时（秒）
    'dns_cache_size': 4096,          # DNS缓存大小
    'dns_max_ttl': 1800,             # DNS最大TTL（秒）
    'dns_min_ttl': 0,                # DNS最小TTL（秒）
    'dns_always_tcp': False,         # 是否总是使用TCP查询DNS
    'dns_no_aaaa': True,            # 是否禁用AAAA查询
    'verbose': True                  # 是否启用详细日志
}

# Glider检查设置
GLIDER_CHECK_SETTINGS = {
    'interval': 30,             # 检查间隔（秒）
    'timeout': 10,              # 检查超时（秒）
    'max_failures': 3,          # 最大失败次数
    'tolerance': 100,           # 延迟容差（毫秒）
    'latency_samples': 10,      # 延迟采样数
    'url': 'http://www.msftconnecttest.com/connecttest.txt',  # 检查URL
    'expect': '200'             # 期望的响应
}

# Glider策略
GLIDER_STRATEGIES = {
    'lha': 'Latency based High Availability mode',
    'ha': 'High Availability mode',
    'rr': 'Round Robin mode',
    'dh': 'Destination Hashing mode'
}

# SSH选项
SSH_OPTIONS = {
    'ServerAliveInterval': '30',      # 保持连接存活间隔（秒）
    'ServerAliveCountMax': '3',       # 最大保持连接尝试次数
    'StrictHostKeyChecking': 'no',    # 是否严格检查主机密钥
    'UserKnownHostsFile': '/dev/null',# 已知主机文件位置
    'TCPKeepAlive': 'yes',           # TCP保持连接
    'ConnectTimeout': '10',          # 连接超时（秒）
    'ExitOnForwardFailure': 'yes',   # 转发失败时退出
    'Compression': 'yes',            # 是否启用压缩
    'ControlMaster': 'no',           # 是否启用连接复用
    'ControlPath': 'none',           # 连接复用路径
    'ControlPersist': 'no',          # 连接复用持续时间
    'BatchMode': 'yes',              # 批处理模式
    'PasswordAuthentication': 'yes',  # 是否允许密码认证
    'PubkeyAuthentication': 'yes'     # 是否允许公钥认证
}