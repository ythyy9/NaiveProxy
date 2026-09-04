# Phase 3 实验矩阵

状态：**BLOCKED_NO_ISOLATED_LAB**

| 实验 | 起点 | 变化 | migration | Xray config test | Xray 启动 | 稳定性 | 结论 |
|---|---|---|---|---|---|---|---|
| E0 旧版控制组 | 2.5.7 冷备 | 无 | 未执行 | 未执行 | 未执行 | 未执行 | NOT_RUN_BLOCKED_NO_ISOLATED_LAB |
| E1 新 Xray + 旧 config | 黄金快照 | 仅替换测试二进制 | 不适用 | 未执行 | 未执行 | 未执行 | NOT_RUN_BLOCKED_NO_ISOLATED_LAB |
| E2 直接 v3.7.0 | 黄金快照 | 文件与 unit 更新 | 不显式执行 | 未执行 | 未执行 | 未执行 | NOT_RUN_BLOCKED_NO_ISOLATED_LAB |
| E3 v3.7.0 + 显式迁移 | 黄金快照 | 文件、unit、migration | 未执行 | 未执行 | 未执行 | 未执行 | NOT_RUN_BLOCKED_NO_ISOLATED_LAB |
| E4 faithful pinned | 黄金快照 | 保留官方必要流程 | 未执行 | 未执行 | 未执行 | 未执行 | NOT_RUN_BLOCKED_NO_ISOLATED_LAB |
| E5 生产安全候选流程 | 黄金快照 | 分离文件、迁移、配置与启动 | 未执行 | 未执行 | 未执行 | 未执行 | NOT_RUN_BLOCKED_NO_ISOLATED_LAB |
| E6 经 v3.3.1 | 黄金快照 | 2.5.7→3.3.1→3.7.0 | 未执行 | 未执行 | 未执行 | 未执行 | NOT_RUN_NOT_REACHED |

## 阻塞证据

- `HypervisorPresent=False`。
- 未发现 Hyper-V VM 服务或 `Get-VM`。
- 未发现 VMware、QEMU、Multipass、Vagrant。
- 未发现现成 Debian ISO 或虚拟磁盘。
- 只有 WSL；任务书明确禁止把 WSL作为完整升级后 systemd/Xray 生命周期的最终证明环境。
- 用户未提供一次性云端 KVM 实验目标。

## 解除阻塞所需输入

提供一个可销毁、可快照、无公网入站的 Debian 12 amd64 完整 VM，并允许：

- 安装任务书列出的实验工具；
- 临时下载固定 GitHub 官方材料；
- 随后阻断生产 IP和公网代理目标；
- 恢复生产冷备；
- 创建和恢复黄金快照；
- 实验结束后销毁 VM和全部快照。
