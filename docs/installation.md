# 安装四节点订阅套件

给 Codex 执行前先读 [任务书](CODEX-DEPLOY.md)。目标是每个客户端一个 HTTPS 链接、四个可用节点。以下命令在自己的 Linux x86_64 + systemd VPS 上以 root 运行。所有示例 IP、域名、邮箱均需替换。

## 1. 盘点与准备

~~~bash
uname -m
ss -lntup
ip -4 route show default
~~~

需要空闲的 TCP 443、本机 TCP 20190 和两组 UDP 范围：28000–28031、28100–28131。TCP 80 供 Certbot standalone 申请与续期，必须在验证时空闲且公网可达。有旧服务占用时先明确迁移方案，不直接停止未知服务。

在商家安全组和现有系统防火墙中放行 TCP 80/443、上述两个 UDP 范围，并保留 SSH。不要暴露 20190 或本机 SOCKS 桥端口。云安全组须允许全部跳跃入口；系统过滤规则须兼容重定向后的两个首端口。不要清空或重置防火墙。

~~~bash
apt-get update
apt-get install -y git curl ca-certificates openssl python3 python3-venv xz-utils nftables
git clone https://github.com/ythyy9/NaiveProxy.git /root/NaiveProxy
cd /root/NaiveProxy
~~~

Hysteria 内置端口范围会创建自己的重定向规则，并在正常停止时移除。不要再叠加手动 NAT 跳跃规则。本套件只接入 IPv4；域名的 A 记录应指向 VPS，没有正确配置 IPv6 就不要保留错误 AAAA。普通 CDN 的代理开关不等于支持 CONNECT 隧道。

## 2. 先验证真实家宽出口

按 [家宽准备](optional-routes.md)建立带认证的本机 SOCKS5 桥，先用实际请求确认出口 IP 与家宽相符。这个桥必须仅监听 127.0.0.1，并在上游故障时失败，不能自动回落到直出。

没有家宽上游时可以继续准备依赖、网站和证书，但不能交付四条可用线路。向使用者获取真实上游，不编造地址或凭据。

## 3. 申请证书

使用独立 Certbot 环境：

~~~bash
python3 -m venv /opt/naive-certbot
/opt/naive-certbot/bin/pip install --upgrade 'certbot>=5.4,<6'
/opt/naive-certbot/bin/certbot --version
~~~

以下两条路线只选一条。证书名统一为 naiveproxy；存在同名证书时先确认归属。

**没有域名，用公网 IPv4：**

~~~bash
/opt/naive-certbot/bin/certbot certonly \
  --standalone --non-interactive --agree-tos --email you@example.com \
  --preferred-challenges http --preferred-profile shortlived --required-profile shortlived \
  --ip-address 203.0.113.10 --cert-name naiveproxy --key-type ecdsa
~~~

**有域名：**

~~~bash
/opt/naive-certbot/bin/certbot certonly \
  --standalone --non-interactive --agree-tos --email you@example.com \
  --preferred-challenges http -d proxy.example.com \
  --cert-name naiveproxy --key-type ecdsa
~~~

命令会接受 Let's Encrypt 服务条款并申请正式证书。IP 证书有效期约 160 小时，依赖可靠续期；参考 [Certbot IP 证书指南](https://letsencrypt.org/2026/03/11/shorter-certs-certbot/) 和 [有效期说明](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability/)。排查 ACME 时可用独立证书名配合 --staging；测试证书不能用于正式连接。

~~~bash
openssl x509 -in /etc/letsencrypt/live/naiveproxy/cert.pem -noout -issuer -dates -ext subjectAltName
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt \
  -untrusted /etc/letsencrypt/live/naiveproxy/chain.pem \
  /etc/letsencrypt/live/naiveproxy/cert.pem
~~~

## 4. 生成每个客户端的四节点订阅

--host 必须对应证书身份；域名路线换成自己的域名。数量按实际需要，下例是五个客户端：

~~~bash
cd /root/NaiveProxy
python3 scripts/configure.py init --host 203.0.113.10 \
  --users friend1 friend2 friend3 friend4 friend5
~~~

编辑私有文件 private/settings.json，把 residential_upstream 从 null 改成已验证的本机桥，例如：

~~~json
"socks5://bridge:你自己生成的桥密码@127.0.0.1:28400"
~~~

这行表示字段的值，并非完整 JSON 文件。桥用户名/密码含特殊字符时需 URL 编码。不要把凭据写进命令行历史；用编辑器修改私有文件。

初始化会给每个客户端生成独立的订阅令牌和四套认证，另外给两个 HY2 服务生成不同的 Salamander 密码。客户端之间必须共享同一入口服务的混淆密码，但认证密码不共用。

~~~bash
python3 scripts/configure.py render private/settings.json
~~~

若上游为空、字段有误、凭据使用占位符或输出目录已存在，命令退出；先修正输入，不绕过校验。生成内容：

| 文件/目录 | 用途 |
| --- | --- |
| private/settings.json | 私有主配置，更新时保留原令牌与未要求改动的凭据 |
| private/rendered/Caddyfile | Naive、网站和私人订阅入口 |
| private/rendered/hy2-direct.json | HY2 直出服务器配置 |
| private/rendered/hy2-residential.json | HY2 家宽服务器配置 |
| private/rendered/subscriptions/ | 每个随机令牌对应四节点的 Base64 内容 |
| private/rendered/clients/friend1/subscription-url.txt | 交给 friend1 的唯一订阅链接 |
| private/rendered/clients/friend1/nodes.txt | 管理员排障时核对四个节点 |
| 同一客户端目录内其他 JSON | 官方 Naive/HY2 客户端排障配置 |

启用的客户端恰好有四个节点；停用的客户端不生成订阅。网站目录 site/ 只放公开网页，不能放这些私有文件。

## 5. 安装三个代理服务

~~~bash
bash scripts/install.sh private/rendered
systemctl status naiveproxy.service naive-hy2@direct.service naive-hy2@residential.service --no-pager
systemctl list-timers naive-cert-renew.timer --all
~~~

脚本用于全新安装：校验发布包、检查端口、创建专用用户、安装三个代理服务与证书 timer，再应用整个配置包。HY2 实例以非 root 用户运行，但为内置 NAT 规则持有 CAP_NET_ADMIN。不修改面板、SSH 和现有代理；放行安全组/过滤规则仍需按主机现状处理。

每次发布的运行配置在 /etc/naiveproxy/releases/ 下，current 符号链接指向当前包。后续更新使用 apply.sh；不要重新初始化凭据，也不要重复运行首次安装脚本。

若此 VPS 已安装仓库旧版的单 Naive 服务，首次安装脚本会拒绝覆盖。Codex 应保留旧账号配置和证书，单独规划迁移到 schema 2、增加缺少的家宽/HY2 认证、部署新 unit 并验证回退。不要直接删除现有安装来绕过检查。

## 6. 外部验收后再交付

从客户端网络验证网站证书，不能只在 VPS 内访问：

~~~bash
curl --noproxy '*' --fail --show-error https://203.0.113.10/
curl --noproxy '*' --fail --show-error https://203.0.113.10/about.html
~~~

给目标客户端添加其 subscription-url.txt 中的单个链接，更新后应显示四个节点。依次选择实际访问，确认两条直出走 VPS，两条家宽走授权家宽出口。用官方排障配置时，可以请求：

~~~bash
curl --noproxy '' --proxy socks5h://127.0.0.1:1080 \
  --connect-timeout 10 --max-time 30 https://www.cloudflare.com/cdn-cgi/trace
~~~

HY2 官方配置的本地 SOCKS 端口分别为 1082/1083。手机或其他客户端不支持完整 Naive 时，不能把只显示两条 HY2 当作完成，详见 [客户端说明](clients.md)。

持续访问 HY2，并用抓包或防火墙计数确认实际更换入口端口；再验证错误认证拒绝、家宽失败不回落、订阅隔离和临时客户端撤销，具体标准见 [Codex 任务书](CODEX-DEPLOY.md)。

~~~bash
/opt/naive-certbot/bin/certbot renew --cert-name naiveproxy --dry-run --run-deploy-hooks
systemctl is-enabled naiveproxy.service naive-hy2@direct.service naive-hy2@residential.service naive-cert-renew.timer
~~~

全部通过后，每个人只收到自己的一个 HTTPS 订阅链接。不要分享整个 private/ 目录或管理员全部客户端资料。
