# 客户端配置

先完成服务端安装。以下三种连接形式不同：

| 形式 | 用途 | 是否保持完整 Naive 行为 |
| --- | --- | --- |
| `naive+https://…` | 支持 Naive 的客户端导入节点 | 取决于该客户端实际使用的 Naive 核心 |
| 本地 `http://127.0.0.1:1081` → Naive → VPS | 给只接受 HTTP 代理地址的软件用 | 使用官方 Naive 时保留 |
| 远程 HTTPS 代理 / HTTP + TLS | v2rayN、小火箭等的兼容入口 | 不保证 Chromium 指纹和 Naive padding |

公网服务器仍使用 HTTPS。不要把节点链接直接改成 `http://VPS:443`。

## v2rayN：优先 Naive

1. 从 VPS 的 `private/rendered/clients/` 安全取回**自己的** `friend1-d.txt`。
2. 在支持 Naive 的 v2rayN 中复制链接后导入；原部署验证过 `7.24.9` 的 Ctrl+V 导入方式。软件界面和核心依赖可能随版本变化。
3. 确认节点类型为 Naive、证书校验开启；选择节点，测试真实网页和出口。
4. 若提示缺少核心或 Cronet 库，使用该版本官方提供的完整核心包，参考 [v2rayN 官方项目](https://github.com/2dust/v2rayN)。不要靠“跳过证书验证”解决证书或核心问题。

v2rayN 自身的本机 HTTP/SOCKS 监听端口以设置页为准。本教程中的 1080/1081 是独立官方 Naive 配置使用的端口，不是所有 v2rayN 版本的默认值。

## 官方 Naive：通用 SOCKS 或本地 HTTP

从 [Naive 稳定发布页](https://github.com/klzgrad/naiveproxy/releases)选择对应操作系统和架构的客户端，核对发布信息和校验值。解压后，把自己的配置放在旁边。

Windows PowerShell：

```powershell
.\naive.exe .\friend1-d-socks.json
```

Linux/macOS：

```bash
./naive ./friend1-d-socks.json
```

此时 SOCKS5 地址是 `127.0.0.1:1080`。只接受 HTTP 地址的软件则改用 `friend1-d-http.json` 启动，填写：

```text
http://127.0.0.1:1081
```

本机到 VPS 仍然走 Naive HTTPS。配置只绑定 `127.0.0.1`，不要改为 `0.0.0.0` 暴露给局域网。每个配置是一个独立启动选项；不要同时启动多个占用相同端口的配置。

## 小火箭 / Shadowrocket：HTTPS 兼容模式

在支持的版本中新增 **HTTPS** 节点，或新增 **HTTP 并启用 TLS**。把自己的参数填入：

| 字段 | 内容 |
| --- | --- |
| 服务器 | `private/settings.json` 中的 `host`，不带 `https://` |
| 端口 | `443` |
| 用户名、密码 | 自己的账号记录 |
| TLS | 开启 |
| 跳过证书验证 / Allow Insecure | 关闭 |
| SNI（若需要填写） | 域名证书填证书对应域名；IP 证书不要编造域名 |

原部署验证过服务端接受普通 HTTPS 代理连接，但没有逐台实测小火箭的版本和界面。若你的版本对 IP 证书或字段支持不同，先查该版本说明；不要把 HTTPS 类型当成已验证的完整 Naive 类型。需要完整 Naive 行为时使用明确支持它的客户端。

## v2rayN：HTTP + TLS 兼容模式

手动新增 HTTP 节点，填写同样的地址、443、用户名和密码，开启 TLS，保持证书校验。原部署使用的版本不能把普通 `https://user:pass@host` 当作 Naive 链接直接导入。

兼容模式依然加密，但仅仅改类型不会增加 Naive padding。[填充协商说明](https://github.com/klzgrad/naiveproxy#opt-in-of-padding-protocol)

## 确认协议与排错

如需检查官方 Naive 的真实协议行为，在**临时副本**配置中加入 `"log-net-log": "netlog.json"`，完成一次请求后正常退出客户端，检查 `HTTP2_SESSION_*` 和请求／响应中的 `padding` 头。日志可能含请求和认证信息，用完在本机删除，不上传公开 Issue。

连接超时先查入口 TCP 443、DNS/安全组和客户端是否走了错误的前置代理；证书报错先查时间、名称和续期；网站可用但代理失败先核对账号与核心。不要为排错关闭 TLS 校验。
