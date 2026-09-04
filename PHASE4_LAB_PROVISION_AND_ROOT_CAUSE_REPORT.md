# Phase 4 实验 VM 建立与根因报告

状态：**BLOCKED_HOST_ADMIN_REQUIRED**
执行时间：2026-09-03（America/Los_Angeles）
工作目录：`PHASE4_20260903-060724`

## 1. 一句话结论

主机硬件、内存、CPU、磁盘和固件虚拟化均满足实验门槛，Phase 3 证据包与美国正式冷备哈希也精确匹配；但当前 Codex 进程没有 Windows 管理员令牌，任务书要求立即停止，因此未安装 VirtualBox、未下载 Debian、未创建网络或 VM、未运行实验，`xray-missing` 根因继续为 `UNRESOLVED`，禁止生产重试。

## 2. Windows 主机环境

| 项目 | 结果 | 门槛 |
|---|---:|---:|
| Windows | Windows 11 专业版，build 26200 | 支持 |
| 当前身份 | `YT\59239` | 已记录 |
| 管理员令牌 | **False** | 必须 True |
| CPU | Intel Core i5-12600KF | 支持虚拟化 |
| 逻辑处理器 | 16 | 至少 4 |
| 总内存 | 31.86 GiB | 至少 12 GiB |
| 审计时可用内存 | 19.15 GiB | 足够分配 4–6 GiB |
| F 盘可用空间 | 873.76 GiB | 至少 60 GiB |
| VirtualizationFirmwareEnabled | True | 必须 True |
| SLAT | True | 必须 True |
| HypervisorPresent | False | 仅记录 |
| winget | 可用 | 安装来源候选 |

资源门槛通过；管理员权限门槛失败。任务书禁止权限绕过，也禁止自动降低 Windows 安全功能。

## 3. VirtualBox

- 精确版本：未安装/未确定。
- 安装动作：未执行。
- Oracle 签名验证：未执行。
- Extension Pack：未安装。
- 既有 VM：未修改或删除。

原因：安装 VirtualBox 驱动和创建 Host-only 网络要求管理员权限，而当前进程不是管理员。

## 4. Debian ISO

- 版本：未下载。
- SHA-512：未计算。
- 签名：未验证。

管理员门禁在下载前失败，因此没有创建可清理的 ISO 或校验文件。

## 5. 网络隔离

- Host-only 网络：未创建。
- NAT 网卡：未创建。
- 端口转发：未创建。
- 桥接网络：未创建。
- Windows 防火墙：未修改。
- Windows 安全功能：未关闭或修改。

## 6. 输入证据验证

### Phase 3 脱敏证据包

```text
SHA-256: E1E5927A5D58A42352BAC692FC853477A31F05B1B31DA7D530A5A19A30700DA1
结果：与任务书期望值精确匹配
```

### 美国正式冷备

```text
SHA-256: 8E468DCAABE86E6B81D4F6D4B56BD07D8652B3D08AB31BAD31B0AFCB589958DE
结果：与任务书期望值精确匹配
```

正式冷备没有移动、改名、覆盖或删除。

## 7. 控制组和实验矩阵

E0–E6 均未运行。没有恢复生产数据库、没有启动实验 x-ui/Xray、没有创建黄金快照。详见 `PHASE4_EXPERIMENT_MATRIX.md`。

## 8. Xray 启动时间线与退出码

未创建实验 VM，因此没有新的 Xray 启动时间线、退出码、config test 或 strace 证据。

## 9. Migration 与数据库

- Migration：`MIGRATION_UNKNOWN`。
- 冷备哈希：已确认完整。
- 实验数据库：未提取、未恢复、未写入。
- Schema/行数：未在实验环境比较。

## 10. 根因代码

**UNRESOLVED**

没有实验数据可满足任何决定性根因代码门槛。

## 11. 置信度

**Low**（针对 `xray-missing` 技术根因）。

对“管理员权限缺失”和“两项输入哈希正确”的判断为高置信度。

## 12. 生产重试资格

**DO NOT RETRY**。

没有旧版控制组、黄金快照、120 秒观察、5 分钟稳定性、两次独立成功路径或实验回滚证据。本轮也没有登录任何生产节点。

## 13. 未解决风险

- 日本和美国生产节点仍为 3x-ui 2.5.7。
- `xray-missing` 根因仍未解决。
- 日美 SOCKS 第二跳仍为 S2：有密码和来源限制，但无传输加密。
- 实验成功未来也只构成生产重试计划依据，不构成生产执行授权。

## 14. VM 销毁结果

没有创建 VM、快照、虚拟磁盘、Host-only 网络、临时 SSH 密钥或一次性密码，因此无需销毁；验证不存在本轮残留虚拟化资源。

## 15. 解除阻塞

关闭当前 Codex 后，以“以管理员身份运行”重新启动 Codex，再执行同一任务书。新的执行必须先复核本报告和 `PHASE4_20260903-060724`，然后从 VirtualBox 来源/版本审计继续；不得重复或覆盖 Phase 2/3证据。
