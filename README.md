# NaiveProxy + HY2：每个客户端一个订阅、四个节点

给 Codex 执行的 VPS 部署套件，也附有中文操作说明。交付目标是 **每个客户端一个独立 HTTPS 订阅链接，更新后获得四个节点**：

| 节点 | 入口 | 出口 |
| --- | --- | --- |
| Naive 直出 | HTTPS / HTTP2，TCP 443 | VPS |
| Naive 家宽 | HTTPS / HTTP2，TCP 443 | 自备家宽 |
| HY2 直出 | Salamander，UDP 28000–28031 跳跃 | VPS |
| HY2 家宽 | Salamander，UDP 28100–28131 跳跃 | 自备家宽 |

浏览器访问 TCP 443 显示正常网站；订阅使用独立随机令牌，不能从一个人的链接取得其他人的节点。**直接把仓库地址和[这份 Codex 任务书](docs/CODEX-DEPLOY.md)交给朋友的 Codex 即可。**

这里是部署材料，不是 NaiveProxy 的上游源码。客户端使用 [klzgrad/naiveproxy](https://github.com/klzgrad/naiveproxy)，服务端使用其指定的 [klzgrad/forwardproxy `naive` 分支](https://github.com/klzgrad/forwardproxy/tree/naive)。普通发行版 Caddy 通常没有这个模块。

```text
浏览器 ────── HTTPS ───────────→ VPS TCP 443 → 普通网页
Naive 客户端 ─ HTTPS / HTTP2 ──→ 同一入口
                                    ├─ 直出账号 → VPS 出口
                                    └─ 家宽账号 → 本机 SOCKS 桥 → 自备家宽出口
HY2 + Salamander + 端口跳跃 ───→ 两组 UDP 入口 → VPS / 家宽
客户端自己的 HTTPS 订阅 ───────→ 四个节点，一次更新
```

## 从哪里开始

1. 准备一台 **Debian 12/13 或 Ubuntu 22.04/24.04、x86_64、systemd** 的 VPS；安装脚本限定 Linux x86_64。有旧服务时先看端口占用。
2. 先准备自己的真实[家宽出口](docs/optional-routes.md)，再按 [安装教程](docs/installation.md) 完成证书、四节点生成、安装和外部验证。**没有域名也可以走 IP 证书路线**。
3. 根据 [客户端教程](docs/clients.md) 添加个人订阅。默认订阅面向支持 Naive 与 HY2 的 v2rayN；其他软件需实测导入兼容性。
4. 日常修改和回退看 [运维说明](docs/operations.md)，Codex 的完成标准见 [任务书](docs/CODEX-DEPLOY.md)。

多客户端一起初始化，例如 `--users friend1 friend2 friend3 friend4 friend5`，会产生五个独立订阅，每个四节点。家宽不是套件免费提供的资源；缺少真实上游时生成器拒绝交付四节点配置，不用直出冒充家宽。

## 这套配置做什么

- 服务端启用认证、`hide_ip`、`hide_via`、`probe_resistance` 和 HTTP/2，正常访问返回静态网页。
- 完整 Naive 客户端使用 Chromium 网络栈并协商 Naive padding；普通 HTTPS 代理兼容模式具有不同的流量特征。[上游设计与填充协议](https://github.com/klzgrad/naiveproxy#padding-protocol-an-informal-specification)
- TLS 校验始终开启；证书由公开 CA 签发。无域名路线采用 Let's Encrypt 短期 IP 证书，并配置自动续期与证书重载。
- HY2 有两套独立实例、账号认证和混淆密码；内置端口范围负责创建与移除自己的 NAT 规则。
- 生成的配置、链接和密码只存入本机 `private/`，不提交 Git。账号变更通过 `apply.sh` 同时更新订阅和服务配置；不修改现有面板、SSH 或其他代理。

它不是“永不被封”的保证，也不把 Salamander 说成 HTTPS 伪装。Naive 提供 TCP 代理；HY2 直出默认允许转发 UDP，家宽默认只转发 TCP，需确认整个家宽桥支持 UDP 后才能调整该设置。

## 版本与验证范围

服务端基线为 [`v2.11.7-naive2`](https://github.com/klzgrad/forwardproxy/releases/tag/v2.11.7-naive2)，下载脚本检查该发布包的 SHA-256。来源部署曾使用官方 Naive `v154.0.8037.49-5` 和 v2rayN `7.24.9` 验证 HTTP/2、双向填充及直出／家宽线路。这是原部署的验证记录，不代表所有手机或本仓库的每种扩展已经实测。

HY2 固定使用官方 [`app/v2.13.0`](https://github.com/HyNetworks/hysteria/releases/tag/app/v2.13.0)，同样校验发布包摘要。仓库的 [自动检查](https://github.com/ythyy9/NaiveProxy/actions) 验证订阅隔离、真实 Naive/HY2 协议、端口变化、家宽失败行为，以及临时 Linux 环境中的安装、更新和防火墙规则生命周期。测试使用临时证书和模拟家宽，不替代实际 VPS 的证书签发与客户端网络验收。

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
