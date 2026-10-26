# 可选扩展：家宽、HY2 与面板

先完成直出配置和外部验证。下面不是主线安装脚本自动完成的内容，需要按自己的环境配置。

## 家宽出口

家宽是出口，不是另一种客户端协议。入口仍是 VPS 的 Naive TCP 443，通过不同用户名分流：

```text
friend1-d → VPS 直出
friend1-r → VPS 本机 127.0.0.1:28400 SOCKS5 → 自备家宽出口
```

你需要先有可用的家宽出口，以及 VPS 到该出口的传输。原方案使用独立 Xray 进程提供带认证的本机 SOCKS 桥，然后连接已有家宽上游。**普通远程 SOCKS5 本身不提供传输加密**；若这一段经过不可信网络，先使用 SSH、WireGuard 或其他合适的加密通道保护它。

已有 Xray 时可参考下面的结构，另存私有 `egress.json`。替换全部 `REPLACE_…`，使用该版本 `xray run -test -c egress.json` 校验，然后用独立服务运行。这个示例不安装 Xray，也不替换现有面板的运行配置。运行时需能找到对应 `geoip.dat`（例如通过 `XRAY_LOCATION_ASSET` 指向实际资产目录）。

```json
{
  "log": {"loglevel": "warning"},
  "inbounds": [{
    "tag": "naive-local",
    "listen": "127.0.0.1",
    "port": 28400,
    "protocol": "socks",
    "settings": {
      "auth": "password",
      "accounts": [{"user": "bridge", "pass": "REPLACE_LOCAL_BRIDGE_PASSWORD"}],
      "udp": false
    }
  }],
  "outbounds": [
    {"tag": "home", "protocol": "socks", "settings": {
      "servers": [{"address": "REPLACE_HOME_OR_TUNNEL_ADDRESS", "port": 1080,
        "users": [{"user": "REPLACE_UPSTREAM_USER", "pass": "REPLACE_UPSTREAM_PASSWORD"}]}]
    }},
    {"tag": "block", "protocol": "blackhole"}
  ],
  "routing": {"domainStrategy": "IPOnDemand", "rules": [
    {"type": "field", "ip": ["geoip:private"], "outboundTag": "block"},
    {"type": "field", "network": "udp", "outboundTag": "block"}
  ]}
}
```

此处的私网规则限制最终访问目标；家宽服务器或本机隧道的地址是下一跳。检查 [Xray SOCKS 入站](https://xtls.github.io/config/inbounds/socks.html)、[SOCKS 出站](https://xtls.github.io/config/outbounds/socks.html) 与 [路由](https://xtls.github.io/config/routing.html)，不要靠关闭整套访问控制来修复连接。

本机桥必须只监听 `127.0.0.1`、启用密码，且家宽故障时请求失败，不要配置自动改走直出的 fallback。先单独验证这个桥的出口，再修改 `private/settings.json`：

```json
{
  "host": "203.0.113.10",
  "residential_upstream": "socks5://bridge:REPLACE_LOCAL_BRIDGE_PASSWORD@127.0.0.1:28400",
  "accounts": [
    {"username": "friend1-d", "password": "REPLACE_KEEP_EXISTING_DIRECT_PASSWORD", "route": "direct", "enabled": true},
    {"username": "friend1-r", "password": "REPLACE_NEW_RANDOM_PASSWORD", "route": "residential", "enabled": true}
  ]
}
```

保留已有直出密码，新增家宽密码用 `secrets.token_urlsafe(32)` 生成。桥密码出现在 URL 中时需 URL 编码；使用 URL-safe 随机字符串最方便。示例占位密码不能直接使用。

按运维说明重新 render、validate、替换配置和 restart。生成器会生成独立的家宽链接。每个人需要两条线路时，为每个人添加一条 `-r` 账号即可。

对两个账号分别检查 `ip=`；再停止自己新增的桥服务，确认家宽账号失败而直出账号仍可用，然后恢复桥。这样才能确认没有无意绕过家宽出口。

## HY2 + Salamander + 端口跳跃

这是另一条独立 UDP 线路。Salamander 把流量混淆为随机字节，不会让它成为普通 HTTPS 网站流量。端口跳跃可以应对部分只针对单个 UDP 端口的限制；对整 IP 或所有 UDP 的封锁没有保证。[官方端口跳跃说明](https://v2.hysteria.network/docs/advanced/Port-Hopping/)

下面是**配置参考**。Hysteria 二进制安装、服务用户、证书权限、续期钩子、防火墙持久化应按自己的系统完成，参考 [官方服务器安装](https://v2.hysteria.network/docs/getting-started/Installation/)。不要把参考片段当成已自动部署的第二套服务。

服务端单端口配置：

```yaml
listen: :28000
tls:
  cert: /etc/hysteria/fullchain.pem
  key: /etc/hysteria/privkey.pem
auth:
  type: password
  password: REPLACE_HY2_AUTH_PASSWORD
obfs:
  type: salamander
  salamander:
    password: REPLACE_SEPARATE_OBFS_PASSWORD
```

客户端配置：

```yaml
server: 203.0.113.10:28000-28031
auth: REPLACE_HY2_AUTH_PASSWORD
tls:
  insecure: false
obfs:
  type: salamander
  salamander:
    password: REPLACE_SEPARATE_OBFS_PASSWORD
transport:
  type: udp
  udp:
    hopInterval: 30s
socks5:
  listen: 127.0.0.1:1082
```

有域名时 `server` 使用证书对应域名。使用的 Hysteria 版本必须支持该客户端格式。服务端仍只监听 28000，因此需要把其他入口端口导向它，例如 Linux IPv4 + iptables 下：

```bash
# eth0 改为真实公网网卡；先确认范围内没有其他服务。
iptables -t nat -A PREROUTING -i eth0 -m addrtype --dst-type LOCAL \
  -p udp --dport 28001:28031 -m comment --comment hy2-hopping \
  -j REDIRECT --to-ports 28000
```

这只是添加一条临时 NAT 规则，重复执行会重复添加。回退用相同命令把 `-A` 改成 `-D`。需另行设置所用防火墙的持久化；不要清空整张规则表。云安全组需放行 UDP 28000–28031；本机过滤规则需允许重定向后的 28000，并符合现有防火墙的规则顺序。IPv6 需单独处理，不能照抄这条 IPv4 规则。

当前上游也提供内置端口范围方式；选择手动 NAT 或该版本支持的内置方式之一，不要盲目叠加。[服务端范围配置](https://v2.hysteria.network/docs/advanced/Port-Hopping/#server)

证书复制到 `/etc/hysteria` 时应只让该服务用户可读，并给它设置自己的续期部署钩子。本仓库的 Naive 钩子只更新 Naive；不能假设 HY2 的证书副本会跟着更新。

Mimic 不是本教程的部署项：官方要求两端 Linux，并且它与端口跳跃互斥，不适合直接套到普通 Windows/iOS 客户端。[Mimic 官方说明](https://v2.hysteria.network/docs/advanced/Mimic/)

## 3x-ui 账号同步的边界

原方案还每分钟读取既有面板账号的启用状态和到期时间，生成对应 Naive 认证；停用或到期时重启 Naive，结束旧连接。它是针对当时数据库结构的私人集成，不是 Naive 或本仓库自带的通用面板功能。

Naive 流量不会自动进入 3x-ui 原有统计；本教程也没有自动期限或流量、IP、设备数量限制。需要集成时应核对当前面板版本、字段与用户映射，再实现同步。原集成只允许无限流量且没有 IP/设备上限的账号；遇到不支持的限制或无法读取策略时停止相关代理，避免绕过约束。

因此这里没有发布固定五人、固定数据库路径和服务器地址的同步脚本。朋友仅需私人使用时按主线管理独立账号；需要面板配额和自动期限时先完成自己的同步与限额验证，再对外提供这一入口。
