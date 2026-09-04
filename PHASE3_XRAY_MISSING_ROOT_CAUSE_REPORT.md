# v3.7.0 `xray-missing` 根因取证报告

状态：**BLOCKED_NO_ISOLATED_LAB**
执行日期：2026-09-03（America/Los_Angeles）
生产写入：**无**

## 1. 一句话结论

既有美国冷备完整且可读取，但当前主机没有符合任务书要求的完整 Debian 12 amd64 systemd 实验 VM，也没有可用的 Hyper-V、VMware、QEMU、Multipass 或一次性云端 KVM 实验目标；因此没有执行任何复现实验，`xray-missing` 根因保持 `UNRESOLVED`，禁止再次尝试生产升级。

## 2. 上一轮证据复核

已完整读取 `PHASE2_SECURITY_AND_3XUI_UPGRADE_REPORT.md`。上一轮确定事实：

- 美国生产节点从 3x-ui 2.5.7 尝试升级到固定 v3.7.0。
- 升级后硬门禁未发现 Xray 子进程，失败标记为 `xray-missing`。
- 冷备回滚脚本输出一次 `ROLLBACK_OK`。
- 回滚后美国恢复为 3x-ui 2.5.7、Xray 25.3.31。
- 数据库 quick_check 和 integrity_check 均为 `ok`。
- 监听语义 diff 为 0 行，BBR/FQ 和 `ens17` root mq 保持。
- 日本未升级，仍为 3x-ui 2.5.7、Xray 25.3.31。

本轮没有把 `xray-missing` 直接归因于 v3.7.0、数据库、Xray 配置或 pinned 脚本。

## 3. 生产节点状态

本轮在发现实验环境不满足硬要求后立即停止，没有重新登录、重启、升级或修改日本/美国生产节点。最近一次已验证生产状态来自紧邻本任务之前完成的回滚核验：

| 节点 | 状态 |
|---|---|
| 美国 | 3x-ui 2.5.7；Xray 25.3.31；x-ui active；Xray 子进程 1；数据库 ok；BBR + FQ；ens17 root mq |
| 日本 | 3x-ui 2.5.7；Xray 25.3.31；x-ui/Xray 正常；BBR + FQ |
| 日美第二跳 | S2；回滚后连接及新 TCP 建连正常 |

本轮未读取或删除生产服务器上的失败现场、冷备或审计目录。

## 4. Migration 状态

分类：**MIGRATION_UNKNOWN**。

上一轮安全脚本跳过了会修改 SSL/Base Path 的整个 `config_after_update` 调用，但 v3.7.0 自身首次启动可能执行自动 schema migration。现有公开证据只能证明升级后检查时没有 Xray 子进程，不能证明 migration 未执行、成功或失败。生产失败现场需在后续具备实验 VM时只读提取并与隔离实验对照。

## 5. 实验环境审计

任务书要求完整 Debian 12 amd64 VM、完整 systemd、独立 PID/网络/文件系统、无公网入站、可快照并可阻断生产 IP。

本机检查结果：

| 项目 | 结果 |
|---|---|
| CPU 虚拟化扩展 | 可用 |
| Windows HypervisorPresent | False |
| Hyper-V 管理模块/Get-VM | 不可用 |
| Hyper-V VM 服务 | 未发现 |
| VMware | 未安装/未发现 |
| VirtualBox | 未安装/未发现；且不在本任务首选路径 |
| QEMU | 未安装/未发现 |
| Multipass/Vagrant | 未安装/未发现 |
| 现成 Debian ISO/VHD/VHDX/VMDK | 在允许的已知目录中未发现 |
| WSL | 存在，但任务书禁止作为最终 systemd/Xray 生命周期证明环境 |
| 一次性云端 KVM VM | 未提供；创建会引入新外部资源和费用授权 |

结论：无法建立满足网络隔离和黄金快照要求的实验环境。不得用 WSL、chroot、Docker 或生产节点替代。

## 6. 冷备验证

本地异地冷备：已验证，未解包生产敏感内容。

| 检查 | 结果 |
|---|---|
| 文件大小 | 197,519,360 bytes |
| SHA-256 | `8e468dcaabe86e6b81d4f6d4b56bd07d8652b3d08ab31bad31b0afcb589958de` |
| 与任务书期望值 | 精确匹配 |
| tar 可读取 | 是，19 个条目 |
| 绝对路径 | 0 |
| `../` traversal | 0 |
| `/etc/x-ui` | 存在 |
| `/usr/local/x-ui` | 存在 |
| `x-ui.db` | 存在 |
| 旧 x-ui 二进制 | 存在 |
| 旧 Xray 二进制 | 存在 |
| systemd unit | 存在 |

正式异地冷备保持原位并继续受当前 Windows 用户独占 ACL 保护。

## 7. 实验矩阵

所有实验均为 `NOT_RUN_BLOCKED_NO_ISOLATED_LAB`。详见 `PHASE3_EXPERIMENT_MATRIX.md`。

没有创建黄金快照，没有恢复生产数据库，没有启动实验面板或 Xray，没有产生启动时间线。

## 8. Xray 错误证据

本轮没有新增 Xray 错误证据。上一轮失败原因只精确到 `xray-missing`，尚不能区分：

- 门禁检查过早；
- Xray 短暂启动后退出；
- 新 Xray 拒绝旧配置；
- 二进制/权限/路径问题；
- migration 缺失或失败；
- pinned 脚本删减了必要流程；
- v3.7.0 数据特异缺陷。

## 9. 二进制和路径验证

本轮仅确认冷备中旧面板、旧 Xray 和 systemd unit 均存在。没有解包到实验根文件系统，也没有在非 VM 环境运行生产副本，因此没有生成可支持运行时根因的 `file/readelf/strace/systemd` 证据。

## 10. 数据库验证

冷备 SHA 和 tar 结构通过。本轮没有从冷备提取 `x-ui.db`，避免在缺乏合格隔离 VM时扩散生产敏感数据。上一轮回滚后的生产数据库 quick_check 和 integrity_check 均为 `ok`。

## 11. 根因代码

**UNRESOLVED**

没有执行 E0–E6，无法满足 G1–G8 任一决定性证据条件。

## 12. 置信度

**Low**

高置信度确认的是“实验环境缺失”和“冷备完整”；对 `xray-missing` 技术根因没有新的运行时证据。

## 13. 推荐升级路径

**DO NOT RETRY**

在提供合格隔离 VM并完成以下门禁前，不得重新升级生产节点：

1. 2.5.7 控制组稳定运行 5 分钟。
2. 新 Xray 对旧 config 的独立测试。
3. E2/E3/E4/E5 均从黄金快照重新开始。
4. 统一 120 秒启动观察，Xray 连续存活 30 秒。
5. 成功路径在独立克隆中重复两次且每次稳定 5 分钟。
6. 实验回滚至少验证一次。

## 14. 生产风险

- 两台生产节点仍为 3x-ui 2.5.7。
- 面板安全隔离或安全升级仍未解决。
- 日美 SOCKS 第二跳仍为 S2：有密码、来源受限，但未加密。
- 本任务没有授权或执行生产升级、SSH加固、面板设置变更或协议迁移。

## 15. 清理结果

- 未创建实验 VM、快照、实验数据库副本或实验 config 副本，因此没有实验敏感数据需要销毁。
- 未创建端口转发或临时防火墙放行。
- 正式美国异地冷备保持不变。
- 本轮只保留脱敏报告、实验矩阵、证据清单、DO NOT RETRY 文件和脱敏证据包。
