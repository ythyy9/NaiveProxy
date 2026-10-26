# NaiveProxy：HTTPS 网站 + 私人代理部署指南

给朋友从零配置 VPS 的中文教程。主线是 **NaiveProxy + HTTPS / HTTP/2 + 正常静态网站**：浏览器访问显示网页，持有账号的 Naive 客户端通过同一个 TCP 443 端口连接。

这里是部署材料，不是 NaiveProxy 的上游源码。客户端使用 [klzgrad/naiveproxy](https://github.com/klzgrad/naiveproxy)，服务端使用其指定的 [klzgrad/forwardproxy `naive` 分支](https://github.com/klzgrad/forwardproxy/tree/naive)。普通发行版 Caddy 通常没有这个模块。

```text
浏览器 ────── HTTPS ───────────→ VPS TCP 443 → 普通网页
Naive 客户端 ─ HTTPS / HTTP2 ──→ 同一入口
                                    ├─ 直出账号 → VPS 出口
                                    └─ 家宽账号 → 本机 SOCKS 桥 → 自备家宽出口（可选）
HY2 + Salamander + 端口跳跃 ───→ 独立 UDP 入口（可选备用）
```

## 从哪里开始

1. 准备一台 **Debian 12/13 或 Ubuntu 22.04/24.04、x86_64、systemd** 的 VPS；安装脚本限定 Linux x86_64。有旧服务时先看端口占用。
2. 跟着 [安装教程](docs/installation.md) 完成证书、账号生成、安装和外部验证。**没有域名也可以走 IP 证书路线**。
3. 根据 [客户端教程](docs/clients.md) 配置 v2rayN、官方 Naive 客户端或小火箭的 HTTPS 兼容模式。
4. 日常改账号、续期和回退看 [运维说明](docs/operations.md)。家宽出口、HY2 和 3x-ui 的适用条件看 [可选扩展](docs/optional-routes.md)。

无需购买家宽出口也可以使用直出。多用户可在初始化时一起生成，例如 `--users friend1 friend2 friend3 friend4 friend5`；每个账号的密码独立。

## 这套配置做什么

- 服务端启用认证、`hide_ip`、`hide_via`、`probe_resistance` 和 HTTP/2，正常访问返回静态网页。
- 完整 Naive 客户端使用 Chromium 网络栈并协商 Naive padding；普通 HTTPS 代理兼容模式具有不同的流量特征。[上游设计与填充协议](https://github.com/klzgrad/naiveproxy#padding-protocol-an-informal-specification)
- TLS 校验始终开启；证书由公开 CA 签发。无域名路线采用 Let's Encrypt 短期 IP 证书，并配置自动续期与证书重载。
- 生成的配置、链接和密码只存入本机 `private/`，不提交 Git。脚本不修改现有面板、订阅、SSH 或防火墙。

它不是“永不被封”的保证，也不把 Salamander 说成 HTTPS 伪装。Naive 主线提供 TCP 代理；需要 UDP 的应用要另选合适的传输方案。

## 版本与验证范围

服务端基线为 [`v2.11.7-naive2`](https://github.com/klzgrad/forwardproxy/releases/tag/v2.11.7-naive2)，下载脚本检查该发布包的 SHA-256。来源部署曾使用官方 Naive `v154.0.8037.49-5` 和 v2rayN `7.24.9` 验证 HTTP/2、双向填充及直出／家宽线路。这是原部署的验证记录，不代表所有手机或本仓库的每种扩展已经实测。

仓库的 [自动检查](https://github.com/ythyy9/NaiveProxy/actions) 在隔离 Linux 环境运行配置生成测试，并启动真正的服务端，验证网站、证书校验、错误认证拒绝、HTTP/2 双向填充及两种出口路由。它不申请公网证书，也不证明某个运营商线路的实际可达性。新 VPS 仍须完成教程中的外部验收。

客户端应跟随 [上游稳定发布](https://github.com/klzgrad/naiveproxy/releases) 更新；升级服务端时同时核对发布版本、包摘要和配置兼容性。

## 仓库内容

| 目录 | 用途 |
| --- | --- |
| `docs/` | 从零安装、客户端、运维和可选扩展 |
| `scripts/` | 本地配置生成、发布包校验、初次安装、续期钩子 |
| `systemd/` | 独立服务和证书续期定时器 |
| `site/` | 可替换的静态网站示例 |
| `tests/` | 配置与协议验证 |

仓库当前内容已替换旧的个人服务器报告。Git 提交历史保留用于回退；这不等于擦除历史记录。
