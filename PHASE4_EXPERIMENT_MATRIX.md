# Phase 4 实验矩阵

状态：**BLOCKED_HOST_ADMIN_REQUIRED**

| 实验 | 起点 | 计划变化 | 实际执行 | 结果 |
|---|---|---|---|---|
| E0 旧版控制组 | 美国 2.5.7 冷备 | 隔离恢复并稳定 5 分钟 | 未执行 | BLOCKED_HOST_ADMIN_REQUIRED |
| E1 新 Xray + 旧 config | 黄金快照 | 仅测试 v3.7.0 Xray | 未执行 | NOT_REACHED |
| E2 直接 v3.7.0 | 黄金快照 | 不显式迁移 | 未执行 | NOT_REACHED |
| E3 v3.7.0 + 显式迁移 | 黄金快照 | 显式 `x-ui migrate` | 未执行 | NOT_REACHED |
| E4 faithful pinned | 黄金快照 | 保留官方必要逻辑 | 未执行 | NOT_REACHED |
| E5 生产安全候选流程 | 黄金快照 | 分离文件/迁移/配置/启动 | 未执行 | NOT_REACHED |
| E6 经 v3.3.1 | 黄金快照 | 分阶段迁移 | 未执行 | NOT_REACHED |

管理员权限门禁在 VirtualBox 安装前失败；未建立实验基线或快照。
