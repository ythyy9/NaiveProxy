# BBR 审计与部署报告

状态：**COMPLETE**
执行日期：2026-09-03（America/Los_Angeles）
执行模式：`SAFE_NATIVE_BBR`

## 1. 一句话结论

日本节点是 Xray TCP 终止型中转：中国侧 VLESS + Reality/TCP 在日本终止，日本 Xray 再建立独立 SOCKS/TCP 连接到美国；日本原本已运行原生 BBR + FQ，本轮补齐 `tcp_bbr` 模块持久化，美国则从 cubic + fq_codel 安全切换为原生 BBR + FQ，因此日本→中国和美国→日本两个 TCP 发送方向均可使用 BBR。

## 2. 实际链路图

```text
中国客户端
→ VLESS + Reality / TCP
→ 日本 MHSanaei/3x-ui 管理的 Xray（终止第一段 TCP）
→ SOCKS / TCP 独立连接（日本现场存在 66 条到美国节点的 Xray TCP socket，Xray UDP socket 为 0）
→ 美国 MHSanaei/3x-ui 管理的 Xray SOCKS inbound（终止第二段 TCP）
→ freedom/direct
→ Internet
```

中转分类：**类型 B，TCP 终止型中转**。不是 DNAT、REDIRECT、TProxy、WireGuard、Hysteria2、TUIC 或 QUIC 主隧道。日本 `ip_forward=0`，未发现 NAT/FORWARD 规则承担该主链路。

## 3. 逐台服务器结果表

| 项目 | 日本 VPS | 美国 VPS |
|---|---|---|
| SSH 连接状态 | 成功审计；临时公钥已删除并复测拒绝 | 成功审计；仅密码认证，临时公钥已删除 |
| OS | Debian GNU/Linux 12 (bookworm) | Debian GNU/Linux 12 (bookworm) |
| 虚拟化 | KVM | KVM |
| 内核 | `6.1.0-49-cloud-amd64` | `6.1.0-10-amd64` |
| 架构 | x86_64 | x86_64 |
| 面板归属 | MHSanaei/3x-ui（高置信度：管理脚本固定指向官方仓库） | MHSanaei/3x-ui（高置信度：管理脚本固定指向官方仓库） |
| 面板版本 | 2.5.7 | 2.5.7 |
| Xray 版本 | 25.3.31 | 25.3.31 |
| systemd 服务 | `x-ui.service`；Xray 是 x-ui 子进程 | `x-ui.service`；Xray 是 x-ui 子进程 |
| 面板二进制 | `/usr/local/x-ui/x-ui` | `/usr/local/x-ui/x-ui` |
| Xray 二进制 | `/usr/local/x-ui/bin/xray-linux-amd64` | `/usr/local/x-ui/bin/xray-linux-amd64` |
| 数据库 | `/etc/x-ui/x-ui.db`（只读 quick_check=`ok`） | `/etc/x-ui/x-ui.db` |
| 运行配置 | `/usr/local/x-ui/bin/config.json` | `/usr/local/x-ui/bin/config.json` |
| 中转/落地角色 | TCP 终止型入口与中转 | SOCKS 第二跳接收与美国落地 |
| 传输层 | 入站 VLESS/Reality/TCP；出站 SOCKS/TCP | 入站 SOCKS/TCP；另有 VLESS/Reality/TCP 入站 |
| 修改前拥塞控制 | bbr | cubic |
| 修改后拥塞控制 | bbr | bbr |
| 修改前默认 qdisc | fq | fq_codel |
| 修改后默认 qdisc | fq | fq |
| 当前出口 root qdisc | `eth0`: fq | `ens17`: mq（安全保留） |
| BBR 是否实际可用 | 是；模块已加载，新连接有 BBR 证据 | 是；模块已加载，新连接有 BBR 证据 |
| 对主链路的影响 | 控制日本→中国方向 TCP 发送 | 控制美国→日本方向 TCP 发送 |
| 服务健康 | x-ui active、Xray 子进程 1、监听零差异 | x-ui active、Xray 子进程 1、监听零差异 |
| 备份目录 | `/root/bbr-audit-20260903-063500` | `/root/bbr-audit-20260903-184926` |

说明：两台独立 `xray.service` 均为 inactive，因为实际 Xray 由 active 的 `x-ui.service` 管理并以子进程运行；这不是故障。

## 4. 日本节点为什么需要 BBR

日本不是纯内核转发。Xray 在日本终止中国侧 VLESS/Reality/TCP，再通过标记为 `us-socks` 的 outbound 建立到美国的独立 TCP socket。现场审计时 Xray 有 132 条 TCP socket，其中 66 条连接美国目标，UDP socket 为 0。因此：

- 日本内核的 TCP 拥塞控制管理日本本机发往中国客户端的 TCP 数据。
- 日本→美国方向由日本发起的 TCP socket，其发送同样受日本内核拥塞控制管理。
- 不能把 BBR描述成降低基础 RTT 的功能；它主要改变 TCP 发送端的拥塞控制。

日本修改前已经是 `bbr + fq`，出口 `eth0` root qdisc 也是 `fq`，配置来源为既有 `/etc/sysctl.d/99-bbr.conf`。本轮没有重复创建 sysctl 配置，只为可加载模块新增开机加载文件。

## 5. 美国节点为什么需要 BBR

美国节点的 SOCKS inbound 接收日本 Xray 建立的 TCP 连接，并从美国侧向日本发送代理响应。该方向属于美国本机产生的 TCP 流量，因此美国发送端可直接使用 BBR。美国修改前为 `cubic + fq_codel`，当前发行版内核已原生提供 BBR，符合无需换内核、无需重启的安全启用条件。

## 6. 实际执行的修改

### 日本 VPS

- 创建 `/etc/modules-load.d/tcp-bbr.conf`，内容仅为 `tcp_bbr`，权限 0644。
- 未创建 `/etc/sysctl.d/99-zz-codex-bbr.conf`；保留并使用既有 `/etc/sysctl.d/99-bbr.conf`。
- sysctl 修改前后均为 `bbr + fq`，没有运行时值变化。
- `eth0` root qdisc 修改前后均为 `fq`，未执行 `tc qdisc replace`。
- 未重启服务或服务器。

### 美国 VPS

- 创建 `/etc/modules-load.d/tcp-bbr.conf`，内容仅为 `tcp_bbr`，权限 0644。
- 创建 `/etc/sysctl.d/99-zz-codex-bbr.conf`，内容仅为：

```text
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
```

- 只运行 `sysctl -p /etc/sysctl.d/99-zz-codex-bbr.conf`，未运行 `sysctl --system`。
- 运行时从 `cubic + fq_codel` 切换为 `bbr + fq`，无需重启。
- 默认出口为 `ens17`；其 root qdisc 是 `mq` 且存在 2 行 class，属于任务书禁止即时替换的复杂结构，因此未执行 `tc qdisc replace`。`net.core.default_qdisc=fq` 已生效，但当前 `mq` 根结构安全保留。
- 未重启服务或服务器。

### 明确未触碰

- 未升级、卸载或迁移 x-ui/3x-ui。
- 未修改 inbound、outbound、路由、UUID、端口、证书、Reality 参数或订阅。
- 未修改 nftables/iptables、防火墙或开放测速端口。
- 未安装自定义内核、BBRv3、Actions-bbr-v3 或任何远程脚本。
- 未修改 GRUB、清理内核、重启网络服务或 VPS。

## 7. 验证结果

### 系统与 TCP

- 两台 `tcp_available_congestion_control` 均包含 `bbr`。
- 两台当前 `tcp_congestion_control=bbr`、`default_qdisc=fq`。
- 两台 `tcp_bbr.ko` 均来自当前 Debian 内核模块目录，并已加载。
- 最终 `ss -tin` 中 BBR 匹配：日本 94，美国 5。连接数量随业务自然变化，只用于证明新连接存在 BBR 状态，不作为性能比例。
- 日本当前出口 root qdisc=`fq`；美国 root qdisc=`mq`，按安全条件保留。

### 面板与代理

- 两台 x-ui 修改前后均为 active。
- 两台均保持 1 个由 x-ui 管理的 Xray 子进程。
- 两台监听端口前后 diff 均为 0 行。
- 两台最近 15 分钟 x-ui 日志均无 `fatal/panic/segfault/failed/error` 匹配。
- 两台最近 15 分钟内核日志均无 `fatal/panic/segfault/BUG/Oops` 匹配。

### 链路测试

| 方向 | 丢包 | RTT min/avg/max | mdev |
|---|---:|---:|---:|
| 日本→美国，20 ping | 0% | 109.952 / 111.523 / 115.482 ms | 1.415 ms |
| 美国→日本，20 ping | 0% | 109.878 / 110.975 / 112.822 ms | 0.886 ms |

没有安全且无需改防火墙的既有 iperf3 路径，未获得可比的前后吞吐测试。日本侧 mtr 未产生可用结果，美国侧未运行 mtr。因此不声称吞吐提升比例，也不声称 BBR 降低了基础 Ping。

### 临时访问清理

- 两台 `/root/.ssh/authorized_keys` 中本轮临时标记均已删除。
- 清理后以对应公钥独立复测，两台均返回认证拒绝（exit 255）。
- 原 `authorized_keys` 的时间戳备份仍保留在各服务器 `/root/.ssh/`，未删除用户恢复点。

## 8. 未完成或 Unknown 项

- 未获得可比的 BBR 启用前后吞吐、重传或实际业务 A/B 数据；本次只能确认配置和 socket 层生效。
- 没有可用 mtr 路径报告。
- 未验证云厂商 Console/VNC/Rescue，因为两台原生 BBR 已可用，不需要进入自定义内核资格流程。
- 无法仅凭瞬时 socket 证明每个历史/备用入站当前都有真实客户端流量；这不影响已验证的主中转结构。

## 9. 精确回滚命令

仅在确需撤销本轮修改时执行。不要卸载正在被 TCP 连接使用的 `tcp_bbr` 模块。

### 日本 VPS

日本的 BBR/FQ sysctl 是本轮前已存在的配置；回滚只删除本轮新增的模块加载文件，不能删除既有 `/etc/sysctl.d/99-bbr.conf`。

```bash
WORKDIR=/root/bbr-audit-20260903-063500
test -r "$WORKDIR/before.env" || { echo 'missing backup'; exit 1; }
source "$WORKDIR/before.env"

rm -f /etc/modules-load.d/tcp-bbr.conf

# 本轮未改变 sysctl 或 eth0 root qdisc；原值本来就是 bbr + fq。
sysctl net.ipv4.tcp_congestion_control
sysctl net.core.default_qdisc
tc qdisc show dev eth0
systemctl is-active x-ui 2>/dev/null || true
systemctl is-active xray 2>/dev/null || true
pgrep -a xray 2>/dev/null || pgrep -af xray-linux 2>/dev/null || true
ss -Hlnptu
```

### 美国 VPS

美国 `ens17` root qdisc 始终为 `mq`，本轮没有即时修改，因此回滚不得执行任何猜测性的 `tc qdisc replace`。

```bash
WORKDIR=/root/bbr-audit-20260903-184926
test -r "$WORKDIR/before.env" || { echo 'missing backup'; exit 1; }
source "$WORKDIR/before.env"

rm -f /etc/sysctl.d/99-zz-codex-bbr.conf
rm -f /etc/modules-load.d/tcp-bbr.conf

sysctl -w "net.ipv4.tcp_congestion_control=${OLD_CC}"
sysctl -w "net.core.default_qdisc=${OLD_DEFAULT_QDISC}"

# before.env 中已核实：OLD_CC=cubic，OLD_DEFAULT_QDISC=fq_codel。
# ens17 root qdisc 未被本轮修改，保持 mq，不执行 tc replace。
sysctl net.ipv4.tcp_congestion_control
sysctl net.core.default_qdisc
tc qdisc show dev ens17
systemctl is-active x-ui 2>/dev/null || true
systemctl is-active xray 2>/dev/null || true
pgrep -a xray 2>/dev/null || pgrep -af xray-linux 2>/dev/null || true
ss -Hlnptu
```

## 10. BBRv3 后续资格判断

| 节点 | 判断 |
|---|---|
| 日本 VPS | **不需要**：当前 Debian 内核原生 BBR 已可用并生效 |
| 美国 VPS | **不需要**：当前 Debian 内核原生 BBR 已可用并生效 |

本轮未下载、安装或运行 Actions-bbr-v3，也不建议 BBRv3 Max、疯批模式或无回滚条件的自定义内核。

## 11. 验收清单

- [x] 日本和美国两台服务器均已连接和审计。
- [x] 面板依据管理脚本仓库、版本、二进制与运行路径识别，未仅凭服务名判断。
- [x] 日本中转归类为 TCP 终止型中转。
- [x] 两台原始拥塞控制和 qdisc 已记录。
- [x] 所有修改前均建立服务器本地 root-only 备份。
- [x] 两台均使用原生 BBR；默认 qdisc 均为 fq。
- [x] 美国复杂 mq 根 qdisc 未即时替换，并记录原因。
- [x] 未修改面板、代理、账号、端口、证书、路由或防火墙。
- [x] 未安装自定义内核，未重启服务器。
- [x] x-ui/Xray 进程、监听端口和日志验证无异常变化。
- [x] 报告含两台独立、精确的回滚命令。
- [x] 未输出密码、私钥、完整 UUID、Reality 私钥或订阅地址。
