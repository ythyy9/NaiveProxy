---
title: 代理服务器搭建档案
type: project
status: reference
updated: 2026-09-03
tags:
  - server
  - proxy
  - x-ui
  - sing-box
  - vless
  - reality
---

# 代理服务器搭建档案

> [!important] 最新交接入口
> 先阅读 [双节点代理项目交接（2026-09-03）](HANDOFF_20260903.md)。本页及 `docs/` 中部分内容是 2026-07 的历史快照，不能替代交接文件中的当前状态。

这个目录用于保留此前搭建代理服务器、调试客户端链路和监控中转流量的资料；当前链路是“日本软银中转 → 美国家宽落地”，服务器管理面板使用 x-ui。[Source: User, 当前对话, 2026-07-18]

```mermaid
flowchart LR
  A["客户端<br/>sing-box TUN"] --> B["日本软银中转"]
  B --> C["美国住宅网络落地"]
  C --> D["互联网"]
```

> [!warning] 敏感资料
> `private-configs/` 内是可直接用于接入的完整客户端配置，包含端点、VLESS UUID 和 Reality 参数。不要公开、提交到父级 Git 仓库或直接分享；根目录的 `.gitignore` 只能降低误提交风险，不能阻止 Obsidian/网盘同步，也不提供加密。[Source: 本地配置安全审计, 2026-07-18]

## 一分钟结论

- 现有 16 份历史配置全部是 **sing-box 客户端侧** 配置，不是 x-ui 服务端备份；它们能说明客户端怎么连入口节点，却不能还原日本中转到美国家宽的第二跳。[Source: 本地配置结构审计, 2026-07-18]
- 最新且最完整的候选配置是 `private-configs/04-jp-softbank-us-lineage/latest-candidate/wangbin-1dbki5bk.json`；它使用 gVisor TUN、XUDP、DNS 劫持及国内直连规则，但是否仍在生产使用需要去客户端或 x-ui 面板确认。[Source: 该配置文件与文件修改时间, 2026-07-17；结论为推断]
- `hk-traffic-monitor/` 是香港中转时期的独立 Git 项目；其数据最后更新于 2026-06-27，当前应视为历史项目或失效监控，除非另行确认香港节点仍在使用。[Source: hk-traffic-monitor/data/traffic.json 与 Git 历史, 2026-07-18]
- 当前目录没有 x-ui 数据库/导出、服务端 Xray 配置、SSH 资料、防火墙规则或第二跳实现，因此仅凭这些文件无法重建现网。[Source: 本地文件清单审计, 2026-07-18]

## 从哪里开始看

1. [当前架构与已知缺口](docs/01-当前架构.md) — 先理解现在的链路，以及哪些信息还没有留下。
2. [配置演变时间线](docs/02-配置演变时间线.md) — 看 2026-06 到 2026-07 做过哪些测试和迁移。
3. [文件索引](docs/03-文件索引.md) — 查每个配置的用途、关系和状态。
4. [安全与恢复边界](docs/04-安全与恢复边界.md) — 明确哪些文件不能公开，以及当前为何不能完整恢复服务器。
5. [接管信息模板](docs/05-接管信息模板.md) — 下次登录服务器时逐项补齐。

## 目录结构

```text
服务器/
├─ README.md                         # 本页
├─ docs/                             # 脱敏后的架构、历史、索引和接管说明
├─ private-configs/                  # 敏感原始 sing-box 配置
│  ├─ 01-us-hk-relay-tests/         # 美国家宽直连 / 香港中转对照
│  ├─ 02-hk-phone-dns-tests/        # 香港手机节点、DNS、UDP、flow 实验
│  ├─ 03-hk-dmit-alternative/       # 香港 DMIT 备选路径
│  └─ 04-jp-softbank-us-lineage/    # 日本入口到美国家宽的配置谱系
└─ hk-traffic-monitor/              # 香港中转流量监控的独立 Git 仓库
```

原始文件只做了目录移动，没有改写；移动前后逐文件 SHA-256 校验一致。[Source: 本次整理校验, 2026-07-18]

## 状态标签

- **用户确认**：由你明确说明，可作为当前事实。
- **文件证实**：能由配置或 Git 历史直接验证。
- **推断**：根据文件名、结构与时间判断，仍需要登录客户端/服务器确认。
- **缺失**：本目录没有足够资料，不能猜测。
