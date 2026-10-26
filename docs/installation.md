# 从零安装

以下命令在自己的 VPS 上运行。支持 Debian 12/13、Ubuntu 22.04/24.04 的 x86_64 + systemd 环境。下面的 `203.0.113.10`、`proxy.example.com`、`you@example.com` 都是占位符，必须替换。

## 1. 检查端口并下载仓库

以 root 登录，或先执行 `sudo -i`：

```bash
uname -m
ss -lntup
```

TCP **443** 需要交给本教程的独立服务；**20190** 只用作回环地址上的 Caddy 管理接口，也不能被占用。TCP **80** 用于 Certbot standalone 验证和续期，平时可以没有进程监听，但每次续期时必须空闲。

若已有网站、REALITY、面板等占用 443，先决定如何迁移那个服务。不要直接运行 `kill`，也不要为了本教程停止不认识的服务。安装脚本遇到占用会退出。HY2 的 UDP 端口和这里的 TCP 443 是不同端口空间，可以共存。

在 VPS 商家安全组和系统防火墙中放行 TCP 80、443；保留自己的 SSH 端口。**不要放行 20190 或后文的 28400**。如果系统已启用 UFW，可以添加 `ufw allow 80/tcp` 和 `ufw allow 443/tcp`；不要为了照抄示例盲目启用、重置防火墙。

```bash
apt-get update
apt-get install -y git curl ca-certificates openssl python3 python3-venv xz-utils
git clone https://github.com/ythyy9/NaiveProxy.git /root/NaiveProxy
cd /root/NaiveProxy
```

有域名时，把 A 记录指向 VPS IPv4，使用仅 DNS 解析。未配置 IPv6 就不要留错误的 AAAA 记录。不要把普通 CDN 的代理开关当作 Naive CONNECT 隧道支持。

## 2. 安装 Certbot

为本教程使用独立虚拟环境，不替换系统已有 Certbot：

```bash
python3 -m venv /opt/naive-certbot
/opt/naive-certbot/bin/pip install --upgrade 'certbot>=5.4,<6'
/opt/naive-certbot/bin/certbot --version
```

IP 证书所需参数与版本见 [Let's Encrypt 的 Certbot 指南](https://letsencrypt.org/2026/03/11/shorter-certs-certbot/)。IP 证书有效期约 160 小时，自动续期必须能长期工作。[证书有效期说明](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability/)

## 3. 申请证书：只选一种

先确认 TCP 80 空闲且公网可以访问。证书名称统一使用 `naiveproxy`；如果 `/etc/letsencrypt/live/naiveproxy` 已存在，先检查它是否就是本次要使用的证书，不要覆盖别的站点。

**A. 没有域名：使用 VPS 公网 IPv4**

```bash
/opt/naive-certbot/bin/certbot certonly \
  --standalone --non-interactive --agree-tos --email you@example.com \
  --preferred-challenges http --preferred-profile shortlived --required-profile shortlived \
  --ip-address 203.0.113.10 --cert-name naiveproxy --key-type ecdsa
```

**B. 有域名：使用自己的域名**

```bash
/opt/naive-certbot/bin/certbot certonly \
  --standalone --non-interactive --agree-tos --email you@example.com \
  --preferred-challenges http -d proxy.example.com \
  --cert-name naiveproxy --key-type ecdsa
```

以上命令会接受 Let's Encrypt 的服务条款并申请正式证书。若需要先排查验证链路，用独立的 `--cert-name naiveproxy-staging --staging` 测试；测试证书不受公众信任，不能用于最终客户端连接。

检查正式证书：

```bash
openssl x509 -in /etc/letsencrypt/live/naiveproxy/cert.pem -noout -issuer -dates -ext subjectAltName
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt \
  -untrusted /etc/letsencrypt/live/naiveproxy/chain.pem \
  /etc/letsencrypt/live/naiveproxy/cert.pem
```

## 4. 生成自己的账号

`--host` 必须与证书中的 IPv4 或域名一致。下面展示五个人；只有自己用就保留 `friend1` 即可。

```bash
cd /root/NaiveProxy
python3 scripts/configure.py init --host 203.0.113.10 \
  --users friend1 friend2 friend3 friend4 friend5
python3 scripts/configure.py render private/settings.json
```

域名路线把 `--host` 改成 `proxy.example.com`。脚本使用系统安全随机源生成不同密码，生成：

- `private/settings.json`：账号主文件，保存好，后续修改以它为准。
- `private/rendered/Caddyfile`：带认证的服务端配置。
- `private/rendered/clients/`：每个账号的导入链接、官方 Naive SOCKS/HTTP 本地监听配置。

默认只创建直出账号，如 `friend1-d`。家宽是[可选扩展](optional-routes.md)，不是免费附送的出口。再次初始化或写入已有输出目录会被拒绝，避免密码意外轮换或留下已停用账号的旧导出。

## 5. 安装独立服务

```bash
bash scripts/install.sh private/rendered
systemctl status naiveproxy.service --no-pager
systemctl list-timers naive-cert-renew.timer --all
```

脚本只接受首次安装，下载固定版本并检查 SHA-256，以独立的 `naiveproxy` 用户运行。配置在 `/etc/naiveproxy`，程序和网页在 `/opt/naiveproxy`。它不安装面板，不调整 BBR，不修改已有代理或防火墙。

默认网站是仓库里的“山间札记”。可以先修改 `site/` 再安装，也可以按运维说明更新部署后的网页。网页目录只放公开内容；**不要放客户端链接、私钥、配置文件或订阅文件**。

## 6. 从另一台设备验证

不要仅在 VPS 内部测试。先用浏览器打开 `https://你的IP/` 或 `https://你的域名/`，必须没有证书警告，并能打开“关于”页面。

从电脑终端检查（Windows 请用 `curl.exe`）：

```bash
curl --noproxy '*' --fail --show-error https://203.0.113.10/
curl --noproxy '*' --fail --show-error https://203.0.113.10/about.html
```

然后按[客户端教程](clients.md)启动对应 Naive 客户端：

```bash
curl --noproxy '' --proxy socks5h://127.0.0.1:1080 \
  --connect-timeout 10 --max-time 30 https://www.cloudflare.com/cdn-cgi/trace
```

直出时，返回的 `ip=` 应是 VPS 对外出口（多网卡或 NAT 环境可能与入口 IP 不同）。家宽账号则应是你自己的家宽出口。

再复制一个客户端配置，故意改错密码并在不同本地端口启动：代理请求应失败。浏览器能够打开网站不能证明认证代理可用；错误密码能够浏览网页也不代表代理认证通过。

最后测试续期：

```bash
/opt/naive-certbot/bin/certbot renew --cert-name naiveproxy --dry-run --run-deploy-hooks
systemctl is-active naiveproxy.service naive-cert-renew.timer
```

必须完成网站、正确账号、错误账号、出口和续期这几项检查，再把每个人自己的链接发给他。不要分享整个 `private/` 目录。
