# SSL 证书配置文档索引

本目录包含股海罗盘 SSL 证书配置的所有相关文档和工具。

---

## 📁 文件列表

### 文档

1. **[SSL_QUICK_START.md](SSL_QUICK_START.md)** - 快速入门指南
   - 5分钟快速配置
   - 生产环境和开发环境的最快配置路径
   - 常见问题解答
   - 快速命令参考

2. **[SSL_CERTIFICATE_SETUP.md](SSL_CERTIFICATE_SETUP.md)** - 详细配置文档
   - 三种完整的配置方案
   - 详细的安装步骤
   - 故障排查指南
   - 安全最佳实践
   - 快速开始脚本

3. **[config.example.yaml](../config.example.yaml)** - 配置示例文件
   - 完整的配置模板
   - SSL 配置示例
   - 其他配置选项说明

### 工具脚本

4. **[setup_ssl.sh](../setup_ssl.sh)** - 自动化配置脚本
   - 一键配置 Let's Encrypt 证书
   - 自动生成自签名证书
   - SSL 状态检查
   - 交互式向导

---

## 🚀 快速开始

### 方案选择

#### 生产环境（推荐）

```bash
# 运行自动化脚本
sudo ./setup_ssl.sh

# 选择 1 (Let's Encrypt + Nginx)
```

详细说明：[SSL_QUICK_START.md](SSL_QUICK_START.md)

#### 开发测试

```bash
# 运行自动化脚本
sudo ./setup_ssl.sh

# 选择 2 (自签名证书 + Flask)
```

详细说明：[SSL_QUICK_START.md](SSL_QUICK_START.md)

---

## 📚 配置方案对比

| 方案 | 适用场景 | 难度 | 成本 | 文档链接 |
|------|---------|------|------|---------|
| **Let's Encrypt + Nginx** | 生产环境 | 中等 | 免费 | [详细配置](SSL_CERTIFICATE_SETUP.md#方案一使用-lets-encrypt-免费证书--nginx推荐生产环境) |
| **自签名 + Flask** | 开发测试 | 简单 | 免费 | [详细配置](SSL_CERTIFICATE_SETUP.md#方案二使用自签名证书--flask-内置-ssl开发测试) |
| **商业证书** | 企业应用 | 中等 | 付费 | [详细配置](SSL_CERTIFICATE_SETUP.md#方案三使用商业-ssl-证书) |

---

## 🔧 常用命令

```bash
# 运行配置向导
sudo ./setup_ssl.sh

# 检查SSL状态
sudo ./setup_ssl.sh  # 选择 4

# Let's Encrypt 证书管理
sudo certbot certificates          # 查看证书
sudo certbot renew --dry-run       # 测试续期
sudo certbot renew                 # 手动续期

# Nginx 管理
sudo nginx -t                      # 测试配置
sudo systemctl reload nginx        # 重新加载
sudo systemctl status nginx        # 查看状态

# 应用管理
python main.py start               # 启动
python main.py stop                # 停止
python main.py restart             # 重启
python main.py status              # 状态
```

---

## 📖 文档导航

### 新手入门

1. 阅读 [SSL_QUICK_START.md](SSL_QUICK_START.md)
2. 运行 `./setup_ssl.sh` 脚本
3. 按提示完成配置

### 高级配置

1. 阅读 [SSL_CERTIFICATE_SETUP.md](SSL_CERTIFICATE_SETUP.md)
2. 选择适合的配置方案
3. 根据需求调整配置参数

### 故障排查

1. 查看 [SSL_CERTIFICATE_SETUP.md](SSL_CERTIFICATE_SETUP.md#故障排查)
2. 运行 `sudo ./setup_ssl.sh` 选择 4 检查状态
3. 查看日志文件

---

## 🔗 外部资源

- [Let's Encrypt 官网](https://letsencrypt.org/)
- [Certbot 官方文档](https://certbot.eff.org/)
- [SSL Labs 测试工具](https://www.ssllabs.com/ssltest/)
- [Nginx SSL 配置文档](https://nginx.org/en/docs/http/configuring_https_servers.html)

---

## 💡 提示

- **生产环境**：推荐使用 Let's Encrypt + Nginx，免费且自动续期
- **开发环境**：使用自签名证书，快速配置
- **测试证书**：使用 SSL Labs 测试工具检查配置
- **监控续期**：Let's Encrypt 证书每 90 天续期一次，系统会自动处理

---

## 📞 获取帮助

如遇到问题：

1. 查看详细文档
2. 运行 `sudo ./setup_ssl.sh` 检查状态
3. 查看日志文件：
   - `/var/log/nginx/error.log`
   - `logs/app.log`

---

**最后更新**: 2025-12-29
