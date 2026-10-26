# 运维、更新与回退

## 服务与文件

| 对象 | 位置 / 名称 |
| --- | --- |
| Naive 服务 | `naiveproxy.service` |
| 证书续期 | `naive-cert-renew.timer` / `naive-cert-renew.service` |
| 服务配置和证书副本 | `/etc/naiveproxy/` |
| 程序和公开网页 | `/opt/naiveproxy/` |
| Caddy 私有运行目录 | `/var/lib/naiveproxy/` |
| Certbot 与证书原件 | `/opt/naive-certbot/`、`/etc/letsencrypt/live/naiveproxy/` |
| 续期部署钩子 | `/etc/letsencrypt/renewal-hooks/deploy/90-naiveproxy` |
| 账号主文件、导出 | `/root/NaiveProxy/private/` |

```bash
systemctl status naiveproxy.service naive-cert-renew.timer --no-pager
journalctl -u naiveproxy.service -n 50 --no-pager
journalctl -u naive-cert-renew.service -n 50 --no-pager
```

本教程不开访问日志，并排除 Caddy 的 HTTP 请求错误日志。分享诊断前仍应检查是否带有节点、地址、密码或访问目标。

## 账号停用、增删与改密

编辑 `private/settings.json`，将账号的 `enabled` 改成 `false` 即停用；删除记录也可以。密码字段可用 `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'` 生成新值后填写。用户名只用字母、数字、下划线和连字符，密码使用脚本生成的 URL-safe 形式。

生成到**新的**目录，验证后替换；不要重新 `init` 覆盖原账号：

```bash
cd /root/NaiveProxy
python3 scripts/configure.py render private/settings.json --output private/rendered-update
/opt/naiveproxy/caddy validate --config private/rendered-update/Caddyfile --adapter caddyfile
cp -a /etc/naiveproxy/Caddyfile /etc/naiveproxy/Caddyfile.previous
install -o root -g naiveproxy -m 0640 private/rendered-update/Caddyfile /etc/naiveproxy/Caddyfile
systemctl restart naiveproxy.service
systemctl is-active naiveproxy.service
```

下次更新换一个新的输出目录名。`restart` 会断开现有连接，让被停用账号的旧 HTTP/2 会话也结束；只做温和 reload 不能用来保证立即撤销已有会话。全部账号停用或删空时仍提供网站，不会生成无认证代理。

如果更新后失败，恢复 `Caddyfile.previous` 再重启。新节点要重新发给相应用户；旧导出文件仍可能带旧密码，自己处理，不要一起分发。

这些账号没有自动到期、流量额度或设备数限制；不要把本教程作为受这些限制的面板账号的旁路。3x-ui 集成边界见[可选扩展](optional-routes.md#3x-ui-账号同步的边界)。

## 证书续期

定时器每六小时检查一次是否需要续期。Certbot 成功签发后，钩子验证证书链、有效期和密钥匹配，复制到服务可读目录，再使用 `reload --force` 加载新证书。续期失败通常不立刻中断已有有效证书；持续失败会在证书到期后影响连接。

```bash
/opt/naive-certbot/bin/certbot renew --cert-name naiveproxy --dry-run --run-deploy-hooks
systemctl start naive-cert-renew.service
openssl x509 -in /etc/naiveproxy/tls/fullchain.pem -noout -dates
```

`dry-run` 检查 ACME 与钩子流程，不需要替换客户端信任设置。若续期成功但复制或重载失败，修复日志中的问题后手动运行：

```bash
/etc/letsencrypt/renewal-hooks/deploy/90-naiveproxy
```

不要等待下一次实际签发才重试部署钩子。standalone 续期要求 TCP 80 可达且空闲；后来新增网站占用 80 时，需要把证书流程改为 webroot 并验证续期，而不是临时关掉未知网站。

## 更新网页或软件

公开网页可直接替换 `/opt/naiveproxy/site/` 中的 HTML，无需重启。使用自己的真实内容，保持链接有效；不要在页面上展示管理接口和代理凭据。

升级服务端先阅读上游发布说明，下载并核对新版本摘要，保留旧二进制，再用新二进制执行 `validate`。通过后在维护时间替换并重启，再验证网站、认证和实际代理。不要反复运行只适用于首次安装的 `install.sh`。

客户端保持跟随上游稳定版本，避免长期停留在旧 Chromium 网络特征；升级后重新检查可用性。

## 停用和恢复

只停用本教程的服务：

```bash
systemctl disable --now naive-cert-renew.timer naiveproxy.service
```

配置、证书和程序保留，可恢复：

```bash
systemctl enable --now naive-cert-renew.timer naiveproxy.service
```

若要彻底卸载，先保存 `private/settings.json` 和仍需要的证书，再检查上表中的文件归属。只删除本教程创建的服务、钩子和目录；不要清理整个 `/etc/letsencrypt`、其他 Caddy 或面板文件。证书删除可使用 Certbot 的 `delete --cert-name naiveproxy`，确认没有其他服务共用它后再执行。

首次安装若中途失败，脚本保留已有新文件并报错。先查失败位置：程序是否下载、服务用户是否已创建、证书是否有效、unit 是否安装。对于已完整安装但启动失败的情况，修复后 `systemctl restart naiveproxy`；若准备重新安装，先按上表核实并移开本次创建的残留文件和服务用户，不要强制绕过“已有安装”的检查。
