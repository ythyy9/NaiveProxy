# 日美双节点第二阶段安全审计与 3x-ui 升级报告

状态：**PARTIAL**
执行日期：2026-09-03（America/Los_Angeles）
固定目标：`v3.7.0`

## 1. 一句话结论

双节点只读安全审计与美国升级前冷备已完成，日美 SOCKS 第二跳归类为 S2；美国固定 v3.7.0 升级因升级后缺少 Xray 子进程触发 `xray-missing` 硬门禁并自动回滚，现已确认恢复为 2.5.7、数据库完整、监听语义零差异，日本按顺序门禁未升级并保持 2.5.7；当前服务器侧 SOCKS/VLESS 监听和日美第二跳正常，但因两台均未完成升级，任务状态为 PARTIAL。

## 2. 上一轮基线复核

与上一轮一致：

- 两台均为 Debian 12、KVM、x86_64。
- 日本内核 `6.1.0-49-cloud-amd64`，美国内核 `6.1.0-10-amd64`。
- 审计时两台均为 3x-ui 2.5.7、Xray 25.3.31。
- 两台 x-ui active/enabled，Xray 各为一个 x-ui 子进程。
- 两台 `tcp_congestion_control=bbr`、`default_qdisc=fq`。
- 日本 `eth0` root qdisc=fq；美国 `ens17` root qdisc=mq。
- 数据库升级前 quick_check 和 integrity_check 均为 `ok`。

没有发现 OS、虚拟化、BBR、qdisc、服务目录或数据库完整性的未知漂移。美国升级失败后已通过直接 root shell 确认自动回滚到原基线。

## 3. 实际链路图

```text
中国客户端
→ 日本 VLESS/REALITY/TCP
→ 日本 Xray
→ 美国 SOCKS/TCP（有密码、无传输加密、仅日本来源获准）
→ 美国 Xray
→ freedom/direct
→ Internet
```

升级中断后服务器侧复核：日本 x-ui/Xray 正常，日本仍有 73 条到美国的 ESTABLISHED TCP 连接，并能向美国 SOCKS 端点新建 TCP；美国 SSH、既有 VLESS 和 SOCKS 精确端点均可达。

## 4. SOCKS 安全审计

分类：**S2——未加密，但来源严格限制**。

| 属性 | 结果 |
|---|---|
| 日本 outbound | SOCKS/TCP |
| 日本 outbound auth | password，1 个用户 |
| transport security | none |
| 美国 inbound | SOCKS/TCP |
| 美国监听地址类别 | all interfaces |
| 美国 auth | password，1 个用户 |
| UDP | disabled |
| 主机防火墙 | nftables；仅允许日本固定来源，其他来源拒绝 |
| 当前连接来源 | 日本 46；其他来源 0（审计时快照） |
| 云安全组 | Unknown |

结论：当前不是公网开放代理，因此没有触发 S3/S4 条件式防火墙修改。密码认证不等于加密，第二跳内容和元数据仍缺少 SOCKS 层加密；协议迁移不在本轮授权范围。

## 5. qdisc 审计

| 节点 | root | 叶子 | 队列数 | drops | backlog | overlimits | requeues | 修改 |
|---|---|---|---:|---:|---|---:|---:|---|
| 日本 | fq | 无独立叶子 | 1 | 未见异常 | 0 | 未见异常 | 未见异常 | 无 |
| 美国 | mq | fq_codel, fq_codel | 2 | 0 | 0 | 0 | 0 | 无 |

美国存在 mq class 行、无 tc filter；`ens17` root mq 始终未替换或删除。

## 6. 内核和更新状态

### 日本

- 运行内核：`6.1.0-49-cloud-amd64`。
- 已安装最高内核：`6.1.0-49-cloud-amd64`。
- `linux-image-cloud-amd64` 已安装：6.1.174-1；候选：6.1.180-1。
- `linux-image-amd64` 未安装；候选：6.1.180-1。
- 待升级包：18。
- reboot-required：否。
- `/boot` 可用约 2.57 GiB。

### 美国

- 运行内核：`6.1.0-10-amd64`。
- 待升级包：142。
- reboot-required：否。
- 已安装最高内核与元包候选：远端私有审计中已采集，但因认证阻塞未取回脱敏摘要，报告为 Unknown。

两台均只执行 `apt-get update`；未安装或删除任何包、内核，未重启 VPS。Console/VNC/Rescue 均为 Unknown。

## 7. SSH 和面板暴露面

| 属性 | 日本 | 美国 |
|---|---|---|
| root 登录 | yes | yes |
| 密码认证 | yes | yes |
| 公钥认证 | yes | no |
| MaxAuthTries | 6 | 6 |
| 面板 HTTPS | 否 | 否 |
| 面板监听 | all interfaces | all interfaces |
| Web Base Path | 自定义 | 默认/短 |
| 2FA | 未启用 | 未启用 |
| 管理员数量 | 1 | 1 |
| 非空 API Token | 0 | 0 |
| 面板来源限制 | Unknown | Unknown |

风险：两台面板均为明文 HTTP 且监听所有接口；是否被本机或云防火墙限制无法完全确认。美国仍仅支持密码 SSH。任务书禁止本轮修改 SSH、面板账号、证书、2FA 或 Base Path，因此未做这些变更。

## 8. 升级材料溯源

- 固定版本：`v3.7.0`。
- 来源：MHSanaei/3x-ui 官方 GitHub tag、release 和 raw tag URL。
- GitHub API：draft=false、prerelease=false，发布时间 2026-08-24。
- 官方 release asset digest 可用并与下载文件匹配：

```text
x-ui-linux-amd64.tar.gz
SHA-256: 0f8dd7baef3458f6591574e24814f322cf7f5e1e27f0a594683745e50be84ec5
```

- 原始 `update.sh` SHA-256：`3eeec8cc2846d788b567f8a1c283901dd71f32a05623783172af5d1bf6839835`。
- 官方 tag `x-ui.sh` SHA-256：`cfabcd4af35a3646c374ea0ccba5178f4c0d3135f699277fc8d8b810158e85c0`。
- Linux 服务器确定性生成的 pinned 脚本 SHA-256：`e11111ef25b590fd1e562b815ec885fda62d60a23300c365bdb6339bd772b7ca`。
- 归档共 17 个条目，无绝对路径或 `../`，包含面板二进制、管理脚本、amd64 Xray 和 Debian unit。
- 三份 shell 脚本均通过 `bash -n`。

Pinned 副本的明确改动：

1. 所有 `main/master` 文件 URL 固定为 `v3.7.0`。
2. 动态 latest 路径不可执行，目标硬固定为 `v3.7.0`。
3. 停止 x-ui 前强制校验官方 asset digest、tar 可读性、架构核心文件和路径安全。
4. 依赖安装改为缺失即停止的只读命令预检，不执行 `apt-get install`。
5. 跳过会自动改变 SSL、Base Path、监听或账号设置的后置向导。
6. `XUI_ENABLE_FAIL2BAN=false`，不安装或配置 fail2ban。

未使用 Dev build、动态 latest、fork、镜像或 `curl | bash`。

## 9. 备份结果

### 美国

- 工作目录：`/root/phase2-security-20260903-192434`，权限 0700。
- 在线 SQLite backup：已创建；最终 SHA 摘要因会话中断未取回。
- 在线 tar：已创建；最终 SHA 摘要因会话中断未取回。
- 冷备：`/root/phase2-security-20260903-192434/private/us-xui-cold-backup.tar`。
- 冷备大小：197,519,360 bytes。
- 冷备 SHA-256：`8e468dcaabe86e6b81d4f6d4b56bd07d8652b3d08ab31bad31b0afcb589958de`。
- 冷备 tar 可读取；冷备完成后旧版 2.5.7 曾确认 active、Xray 子进程为 1。
- 回滚脚本：`/root/phase2-security-20260903-192434/rollback/rollback-xui.sh`，可执行且 `bash -n=0`。
- 异地副本：已验证；本地与远端 SHA-256 完全一致，文件 ACL 仅授予当前 Windows 用户。

### 日本

- 审计工作目录：`/root/phase2-security-20260903-072218`，权限 0700。
- 因美国未完成验证，日本没有进入升级阶段，故未制作升级冷备或回滚脚本。
- 日本原有 2.5.7 始终 active；未停止服务。

## 10. 美国升级结果

状态：**ROLLED BACK / 回滚成功**。

- 升级前：2.5.7、Xray 25.3.31、数据库完整、业务正常。
- 升级后的硬验证未发现 Xray 子进程，失败原因文件明确记录 `xray-missing`。
- 自动回滚脚本输出 1 个 `ROLLBACK_OK`，退出后的直接 root shell 复核显示：x-ui active、版本 2.5.7、Xray 25.3.31、Xray 子进程 1。
- 回滚后数据库 quick_check=`ok`、integrity_check=`ok`。
- 回滚后监听语义 diff 为 0 行；SSH、既有 VLESS 和 SOCKS 端点均开放。
- 日本侧显示到美国的已建立连接 73，并能新建 SOCKS TCP 连接。
- BBR/FQ 保持，`ens17` root qdisc 仍为 mq。
- 未再次尝试美国升级；依据任务书，美国回滚后禁止继续升级日本。

## 11. 日本升级结果

状态：**SKIPPED BY SAFETY GATE**。

- 当前确认仍为 3x-ui 2.5.7、Xray 25.3.31。
- 中国侧 VLESS/REALITY inbound、日本→美国 SOCKS outbound 和路由在审计时完整。
- 因美国未完成全部 F 阶段验证，日本升级被禁止，没有执行。
- 日本临时公钥删除前标记数 1，删除后 0；相同私钥复测 exit 255、认证拒绝。

## 12. 最终服务验证

| 检查 | 结果 |
|---|---|
| 日本 x-ui | active，2.5.7 |
| 日本 Xray | 1 个子进程 |
| 日本→美国 ESTABLISHED TCP | 73（中断后快照） |
| 日本→美国新 TCP | 成功 |
| 美国 SSH 精确端点 | 可达 |
| 美国 VLESS 精确端点 | 可达 |
| 美国 SOCKS 精确端点 | 可达 |
| 美国 x-ui 版本/数据库 | 已回滚为 2.5.7；quick/integrity 均为 ok |
| 美国回滚后监听语义 | 与升级前一致，diff 0 行 |
| BBR/qdisc 升级后复核 | 两台保持 bbr + fq；美国 root mq 保持 |
| 中国大陆客户端实机 | Unknown，需用户确认 |

服务器侧代理第二跳目前可用；中国大陆客户端实机连接和速度仍需用户侧确认。

## 13. 实际执行的修改

- 两台创建了 root-only 第二阶段审计工作目录和审计文件。
- 两台刷新 apt 索引；未安装包。
- 美国短暂停止并重新启动旧版 x-ui 以制作冷备。
- 美国启动固定 v3.7.0 升级脚本；升级后因 `xray-missing` 自动执行冷备回滚，恢复为 2.5.7。
- 日本未升级、未重启面板。
- 没有修改 BBR/FQ、美国 mq、防火墙、SOCKS/VLESS/Reality、UUID、凭据、端口、证书、Base Path、2FA 或 SSH 配置。
- 日本临时公钥已删除并复测拒绝；美国本轮未建立可用临时公钥。
- 本机临时冷备副本、一次性执行脚本和已使用的 release archive 均已删除；只保留受限 ACL 的正式异地冷备。

## 14. 精确回滚命令

### 美国

本轮已自动执行下列回滚脚本并得到 `ROLLBACK_OK`；脚本继续保留，可在未来确需恢复同一冷备时使用：

```bash
systemctl is-active x-ui || true
/usr/local/x-ui/x-ui -v 2>/dev/null || true
pgrep -af 'xray-linux|/xray' || true

bash /root/phase2-security-20260903-192434/rollback/rollback-xui.sh
```

脚本已恢复冷备中的 `/usr/local/x-ui`、`/etc/x-ui`、`/usr/bin/x-ui`、systemd unit 和可选环境文件，执行 daemon-reload/enable/start，并验证 2.5.7、数据库、Xray、BBR/FQ 和 ens17 root mq。它没有修改防火墙或 BBR配置。

回滚后复核：

```bash
/usr/local/x-ui/x-ui -v
systemctl is-active x-ui
pgrep -af 'xray-linux|/xray'
python3 - <<'PY'
import sqlite3
p='/etc/x-ui/x-ui.db'
c=sqlite3.connect(f'file:{p}?mode=ro', uri=True)
print(c.execute('PRAGMA quick_check').fetchone()[0])
print(c.execute('PRAGMA integrity_check').fetchone()[0])
PY
sysctl net.ipv4.tcp_congestion_control
sysctl net.core.default_qdisc
tc qdisc show dev ens17
```

### 日本

日本未升级，无面板回滚操作。不要运行美国回滚脚本，也不要删除日本现有面板文件。

## 15. 未完成和后续任务

本轮恢复动作已经完成。后续如要再次升级，必须先独立诊断 v3.7.0 首次启动为何未拉起 Xray；不得在未理解 `xray-missing` 原因时重复生产升级，也不得跳过“美国验证成功后才升级日本”的顺序门禁。

后续独立任务：

- 内核安全更新与逐台重启。
- 美国 SSH 公钥化。
- 面板 HTTPS、2FA、非默认 Base Path 和来源限制。
- SOCKS 第二跳迁移到加密协议。
- 中国客户端实机验证。
- 性能 A/B 基线。

本轮没有自动执行上述后续任务。

## 16. 当前验收结论

- [x] 已读取上一轮 BBR 报告。
- [x] 两台身份、服务、数据库、BBR 和 qdisc 基线已复核。
- [x] SOCKS 第二跳完成 S2 分类，未输出凭据或真实端口。
- [x] 美国 mq 及全部叶子 qdisc 已审计且未修改。
- [x] 已审计 SSH、面板暴露、内核和待升级包。
- [x] 固定目标 v3.7.0，官方 digest 匹配，无 Dev/latest/管道执行。
- [x] 美国升级前冷备、回滚脚本和异地副本已验证。
- [x] 美国升级失败后已自动回滚，2.5.7、数据库、Xray、监听和 BBR/qdisc 已复核。
- [ ] 日本升级未执行（正确受美国门禁阻止）。
- [x] 日本临时 SSH 公钥已删除并复测拒绝。
- [x] 美国最终状态已通过直接 root shell 确认。
- [x] 临时下载、一次性脚本和未使用 release archive 已清理。

因此最终状态必须为 **PARTIAL**。
