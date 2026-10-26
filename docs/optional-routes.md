# 家宽准备与协议边界

四节点方案的家宽出口是必需输入。仓库不提供第三方账号，也不把某个 VPS 出口标成家宽。

## 本机 SOCKS5 桥

~~~text
Naive 家宽 ─┐
            ├→ 127.0.0.1:28400，带认证 SOCKS5 → 自备家宽上游
HY2 家宽 ───┘
~~~

使用已有可靠桥也可以，只要它仅监听回环地址、需要认证、出口验证正确，并且上游不可用时不会直出回落。

原部署使用独立 Xray 进程桥接既有 SOCKS5 上游。Codex 可以使用已有兼容 Xray，或从 [Xray 官方发布](https://github.com/XTLS/Xray-core/releases)安装当前受支持版本并核对校验信息。不要改写面板正在使用的运行配置。

示例另存私有 /etc/naive-egress/config.json，替换所有占位符：

~~~json
{
  "log": {"loglevel": "warning"},
  "inbounds": [{
    "tag": "local",
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
    {"tag": "blocked", "protocol": "blackhole"}
  ],
  "routing": {"domainStrategy": "IPOnDemand", "rules": [
    {"type": "field", "ip": ["geoip:private"], "outboundTag": "blocked"},
    {"type": "field", "network": "udp", "outboundTag": "blocked"}
  ]}
}
~~~

对应 [SOCKS 入站](https://xtls.github.io/config/inbounds/socks.html)、[SOCKS 出站](https://xtls.github.io/config/outbounds/socks.html)、[路由](https://xtls.github.io/config/routing.html)。需要 geoip.dat；设置 XRAY_LOCATION_ASSET 指向实际资产目录，再运行该版本的配置检查：

~~~bash
XRAY_LOCATION_ASSET=/opt/naive-egress /opt/naive-egress/xray run -test -c /etc/naive-egress/config.json
~~~

示例服务（路径和用户按实际安装调整）：

~~~ini
[Unit]
Description=Authenticated loopback SOCKS bridge to residential exit
Wants=network-online.target
After=network-online.target

[Service]
User=naive-egress
Group=naive-egress
Environment=XRAY_LOCATION_ASSET=/opt/naive-egress
ExecStart=/opt/naive-egress/xray run -c /etc/naive-egress/config.json
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
~~~

先创建对应无登录服务用户，以 root 拥有配置，给服务组只读权限；程序与资产放入 /opt/naive-egress。保存 unit 后 daemon-reload、enable --now，并单独测试出口。这里需要使用者提供真实上游，因此不会由套件猜测并自动安装一个假桥。

远程普通 SOCKS5 本身不提供加密。如果 VPS 到家宽这一段经过不可信网络，应使用 SSH、WireGuard 或其他已验证的加密通道保护它；桥也可以接入本机隧道端点。验证时区分最终目的地 ACL 和下一跳地址，不靠关闭全部访问限制修复配置。

本套件只接受回环 SOCKS URL，私有 settings.json 的 residential_upstream 填入这个桥。桥密码含特殊字符时 URL 编码。桥未验证前不要交付家宽节点。

## HY2 已是完整安装项

安装脚本下载经过摘要校验的 Hysteria 2.13.0，生成并启动直出、家宽两个实例。两者均启用 userpass 认证和 Salamander，使用不同入口范围与混淆密码。客户端的认证与订阅令牌独立。

服务器 listen 使用端口范围，并通过 Hysteria 内置机制创建重定向规则。服务有 CAP_NET_ADMIN，系统需安装 nftables。**不要再复制旧的手动 iptables 跳跃规则。** [上游端口范围机制](https://v2.hysteria.network/docs/advanced/Port-Hopping/)

v2rayN 订阅采用“数字首端口 + mport 范围”格式；官方 Hysteria 客户端 JSON 直接使用 server 多端口格式。mport 是客户端约定，不能假定所有软件都支持；在目标软件中检查导入结果并实际观察跳跃。[上游 URI 说明](https://v2.hysteria.network/docs/developers/URI-Scheme/)

Salamander 混淆不等于 HTTPS 外观。Mimic 没有启用，它与端口跳跃互斥且要求两端 Linux。[Mimic 说明](https://v2.hysteria.network/docs/advanced/Mimic/)

## 面板与授权边界

原私人部署还有读取既有 3x-ui 账号启停和到期状态的定制同步。本仓库的四节点套件使用独立客户端记录，不自动接入数据库、订阅或流量统计。

本套件没有流量额度、自动到期、IP/设备限制。若用户已有这些限制，Codex 必须保留约束，完成相应集成后才能让同一账号使用新入口；不能把“独立账号”当作绕过限制的理由。

一客户端一链接表示独立的订阅和认证材料，不代表硬件绑定。链接拥有者可以转交它；泄露后需要轮换订阅令牌和四套节点密码。
