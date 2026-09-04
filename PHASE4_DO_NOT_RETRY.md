# Phase 4：禁止生产重试

状态：**DO NOT RETRY**

本轮因当前 Codex 进程没有 Windows 管理员权限而停止，未创建隔离 VM，也没有获得新的根因证据。

在以管理员身份重新运行任务书并完成全部实验门禁前：

1. 不得再次升级美国生产节点。
2. 不得升级日本生产节点。
3. 不得用 WSL、Docker、chroot 或生产 VPS代替完整实验 VM。
4. 不得把 `xray-missing` 归因于 v3.7.0、migration、Xray配置或 pinned脚本。

本文件不构成生产执行授权。
