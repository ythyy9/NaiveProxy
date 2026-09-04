# 日本 VPS 重装后 SSH 修复与 3x-ui 安装报告

状态：**COMPLETE**
执行日期：2026-09-03（America/Los_Angeles）

## 1. 结论

日本 VPS 重装导致的 SSH host key 冲突已安全修复；随后在确认系统干净后，从 MHSanaei/3x-ui 官方固定 `v3.7.0` release archive 完成全新安装。3x-ui、Xray、数据库、配置测试和面板监听均验证正常，临时 SSH 公钥已撤销。

## 2. SSH 修复

- 目标：重装后的原日本 VPS 地址。
- 原因：本地 `known_hosts` 保留了重装前的 ED25519、RSA 和 ECDSA key。
- 新 ED25519 指纹经截图和真实 SSH 握手交叉核对：

```text
SHA256:IoTohBqqCw/dbbVqCi7z6tRE1SLrHNXLgwwkqBxe/mg
```

- 修改前已备份：

```text
C:\Users\59239\.ssh\known_hosts.before-jp-reinstall-20260903-084230
```

- 只删除该目标的3条旧记录，写入1条新 ED25519记录。
- 严格 host key 校验复测成功到达密码认证阶段，不再出现 host key changed。

## 3. 安装前基线

| 项目 | 结果 |
|---|---|
| OS | Debian GNU/Linux 12 (bookworm) |
| 架构 | x86_64 |
| 内核 | 6.1.0-13-cloud-amd64 |
| 虚拟化 | KVM |
| SSH | active |
| 旧 x-ui目录 | 不存在 |
| 旧 x-ui unit | 不存在 |
| apt/dpkg锁 | 无 |
| 主机防火墙规则 | 未检测到现有 nftables/iptables规则 |
| 初始监听数量 | 2 |

## 4. 安装材料与方法

- 来源：官方 `MHSanaei/3x-ui`。
- 固定版本：`v3.7.0`；未使用动态 latest、Dev build、fork或镜像。
- Release archive：`x-ui-linux-amd64.tar.gz`。
- Archive SHA-256：

```text
0f8dd7baef3458f6591574e24814f322cf7f5e1e27f0a594683745e50be84ec5
```

- 官方 Release API digest与本地下载精确匹配；release不是draft或prerelease。
- 固定tag管理脚本SHA-256：

```text
cfabcd4af35a3646c374ea0ccba5178f4c0d3135f699277fc8d8b810158e85c0
```

- Tar路径无绝对路径或`../` traversal，核心amd64面板/Xray/unit文件存在且非空。
- 没有执行`curl | bash`；采用下载、校验、解包、安装的分离流程。
- 安装的必要Debian依赖：ca-certificates、cron、curl、openssl、python3、socat、tar。
- 未安装fail2ban、VirtualBox Extension Pack或第三方网络调优脚本。

## 5. 面板安全初始化

- 自动生成随机管理员用户名和高强度随机密码。
- 自动选择空闲随机高端口。
- 自动生成自定义随机Web Base Path。
- 凭据仅保存在日本服务器：

```text
/root/3x-ui-access.txt
```

- 文件属主：`root:root`；权限：0600。
- 本报告不包含用户名、密码、真实面板端口或完整URL。

## 6. 验证结果

| 检查 | 结果 |
|---|---|
| 3x-ui版本 | 3.7.0 |
| Xray版本 | 26.7.28 |
| x-ui service | active、enabled |
| Xray子进程 | 1 |
| Xray连续存活门禁 | 30秒通过 |
| 数据库quick_check | ok |
| 数据库integrity_check | ok |
| Xray config test | exit 0 |
| 管理员数量 | 1 |
| 业务inbound数量 | 0 |
| 面板监听 | 存在；从本机TCP可达 |
| 严重安装日志匹配 | 0 |

当前Xray仅包含面板内部运行所需的基础/tunnel结构；没有创建生产VLESS、Reality、SOCKS或日本→美国outbound。

## 7. 当前安全状态

- 面板监听所有接口。
- 当前未配置HTTPS。
- 主机未检测到现有防火墙限制，本轮也未擅自创建规则。
- 随机高端口和自定义路径只能降低误发现概率，不能替代HTTPS、2FA或来源限制。

建议在录入生产代理配置前单独完成：HTTPS或仅本地/SSH隧道访问、2FA、管理端来源限制和防火墙设计。

## 8. 临时访问与文件清理

- 临时SSH公钥标记删除前：1。
- 删除后：0。
- 使用相同私钥复测：exit 255，认证拒绝。
- 第一次因本地脚本摘要SIGPIPE误触发的安装已完整回滚，其临时目录已删除。
- 成功安装目录中的release archive和敏感设置输出已删除。
- 本地临时安装脚本和主机key捕获文件已删除。
- 保留正式安装工作目录中的脱敏日志、小型vendor元数据和回滚脚本。

## 9. 回滚

全新安装回滚脚本：

```text
/root/3x-ui-install-20260903-114945/rollback-fresh-install.sh
```

该脚本会停止/禁用x-ui，并删除本轮全新创建的x-ui unit、二进制、数据库目录和凭据文件。仅在明确决定卸载本轮安装时执行。

## 10. 未恢复事项

- 重装前的日本3x-ui数据库和代理配置没有本地服务端冷备可用于恢复。
- 日本→美国生产中转链路尚未重建。
- BBR/FQ状态和重装后的系统加固不属于本次“SSH修复+安装3x-ui”范围，未自动配置。
- Codex 404和ChatGPT登录500问题未在本任务中处理；它们与日本VPS SSH host key修复是不同故障域。
