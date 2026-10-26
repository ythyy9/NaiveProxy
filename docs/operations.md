# 账号、订阅、续期与回退

## 文件与服务

| 对象 | 位置 / 名称 |
| --- | --- |
| Naive、网站、订阅 | naiveproxy.service |
| HY2 直出 / 家宽 | naive-hy2@direct.service / naive-hy2@residential.service |
| 证书续期 | naive-cert-renew.timer / naive-cert-renew.service |
| 当前运行配置包 | /etc/naiveproxy/current → /etc/naiveproxy/releases/bundle.* |
| 上一成功配置包 | /etc/naiveproxy/previous |
| 共用证书副本 | /etc/naiveproxy/tls/ |
| 程序与公开网页 | /opt/naiveproxy/ |
| 证书原件 | /etc/letsencrypt/live/naiveproxy/ |
| 续期钩子 | /etc/letsencrypt/renewal-hooks/deploy/90-naiveproxy |
| 账号主配置和交付文件 | /root/NaiveProxy/private/ |

~~~bash
systemctl status naiveproxy.service naive-hy2@direct.service naive-hy2@residential.service --no-pager
journalctl -u naiveproxy.service -u naive-hy2@direct.service -u naive-hy2@residential.service -n 50 --no-pager
journalctl -u naive-cert-renew.service -n 50 --no-pager
~~~

不开网站访问日志，并排除 Caddy 的 HTTP 请求错误日志；HY2 只记录 warning 及以上级别。日志仍应在分享前检查是否带有私密数据。

## 修改客户端与更新订阅

以原 private/settings.json 为准。每个 clients 元素就是一个客户端，含 enabled、subscription_token 和四套协议/出口认证。

- 停用：将该客户端 enabled 改为 false，会同时撤销订阅与四条认证。
- 改某一节点密码：只更新对应 naive/hy2 的 direct/residential 密码。
- 只换订阅链接：生成新的 subscription_token。**只换令牌不会使已导入的节点密码失效**；链接泄露时也要换该客户端的四个密码。
- 正常维护：保持令牌不变，用户更新原链接即可取得新节点。
- 新增：按 schema 2 添加完整客户端，所有令牌和密码独立；不要复制别人的凭据。

生成密码或订阅令牌：

~~~bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
~~~

编辑后，生成到一个尚不存在的新目录并应用：

~~~bash
cd /root/NaiveProxy
python3 scripts/configure.py render private/settings.json --output private/rendered-update
bash scripts/apply.sh private/rendered-update
~~~

下次更新换一个新输出目录。apply 会先验证 Caddy 配置、暂存整个包，再短暂停止三个代理并切换 current，随后启动和检查服务。重启会结束旧 HTTP/2 和 QUIC 会话；只重载网站配置不足以保证账号立即撤销。

失败时脚本尝试恢复此前包及此前运行的服务，并保留故障配置供诊断；首次安装没有旧包时停止服务并报错。检查实际状态，不能把“尝试回退”当成“已恢复”。成功后仍需从外部回读订阅并检查受影响节点。

旧的订阅内容保留在私有历史包里，但公开 /s/ 只读取 current/subscriptions。旧交付目录也可能含旧密码，不能一起分发。上一包仍用于回退；更旧的包可以在不再需要恢复时由管理员核实路径后清理。

## 回退配置

确认 previous 指向需要恢复的成功包，然后：

~~~bash
readlink -f /etc/naiveproxy/previous
bash /root/NaiveProxy/scripts/apply.sh /etc/naiveproxy/previous
~~~

回退恢复的是运行包，私有 settings.json 需要同步恢复对应版本，避免下一次 render 又覆盖回退结果。保存主配置备份属于管理员责任，不把含密码的备份提交 Git。

## 证书续期

定时器每六小时检查一次是否需要续期。成功签发后的钩子验证证书链、有效期和密钥匹配，更新共用证书副本。Naive 使用 reload --force 加载新证书，Hysteria 在新握手时读取证书文件。

~~~bash
/opt/naive-certbot/bin/certbot renew --cert-name naiveproxy --dry-run --run-deploy-hooks
openssl x509 -in /etc/naiveproxy/tls/fullchain.pem -noout -dates
~~~

如果已签发但钩子失败，修复后手动重跑：

~~~bash
/etc/letsencrypt/renewal-hooks/deploy/90-naiveproxy
~~~

不要只等待下一次签发。standalone 验证依赖公网 TCP 80 可达且空闲；以后新增网站占用 80 时，需要正式改为 webroot 等验证方式并重新验证续期。IP 短期证书不适合长期忽略续期失败。

## 家宽、UDP 与额度

家宽桥需独立维护。HY2 家宽默认 disable_udp=true，因为常见本机桥只转发 TCP；只有验证整条上游链支持 UDP 后才改为 false。HY2 的外层传输一直使用 UDP，这个字段只控制被代理应用的 UDP 转发。Naive 两个节点始终是 TCP 代理。

本套件没有到期、流量、IP、设备数量限制，也不会自动计入 3x-ui。不能作为受限面板账号的无限制旁路；需要这些功能时按 [面板边界](optional-routes.md#面板与授权边界)单独实现和验证。

## 更新和停用

网页可替换 /opt/naiveproxy/site/ 下的公开 HTML，无需重启。升级程序先核对官方发布、摘要和兼容性，保留旧二进制，验证后替换并重启受影响服务。

只停用本套件：

~~~bash
systemctl disable --now naive-cert-renew.timer naiveproxy.service naive-hy2@direct.service naive-hy2@residential.service
~~~

HY2 正常停止时移除自己创建的跳跃规则；核对规则，不清空整张防火墙。配置和证书保留，可恢复：

~~~bash
systemctl enable --now naive-cert-renew.timer naiveproxy.service naive-hy2@direct.service naive-hy2@residential.service
~~~

卸载时只处理表中已核实归属的目录、服务和钩子。不要删除整套 /etc/letsencrypt、其他 Caddy、面板或未知家宽桥。首次安装中断时先检查残留与日志，不能靠强制删除全部配置制造“全新环境”。
