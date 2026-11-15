# 2026-11-15 全新 Debian 13 VPS 阶段验收

本记录来自本轮实际 SSH 操作和 Windows 官方 Hysteria 客户端测试，独立于旧测试机 `helan` 的历史结果。仅修改 `liucong552-art/hy2jieshu`；`jieshu` 全程只读。公开记录不包含服务器真实地址、邮箱、节点链接、密码、私钥或原始日志。

**最终真机结论：常用HY2管理、保护、真实业务、两次重启、keep/purge卸载重装和测试清理通过；最终主节点外部客户端通过，严格doctor为0错误0警告。** Linux166项测试通过，最终文档提交CI由收尾提交核对。 长期、破坏性和缺少网络条件的场景保留未测状态，不能宣称所有场景已完成。

## 环境与部署

| 项目 | 本轮实际结果 |
|---|---|
| 服务端 | 全新 Debian 13.5，Linux `6.12.88+deb13-amd64`，x86_64，2 GiB 内存 |
| 管理连接 | 使用用户授权的 SSH 私钥成功登录；未公开密钥内容 |
| DNS | Windows 与 VPS 分别查询，域名 A 记录均指向当前 VPS |
| 前置检查 | `hy2_fresh_preflight.sh before`、`manager`、`main` 全部 PASS |
| TLS | 实际取得 ZeroSSL ECC 正式证书，有效期 2026-11-15 至 2027-02-13；客户端保持证书与 SNI 验证 |
| 核心与客户端 | Hysteria `2.14.0`；Windows 官方客户端，不使用跳过证书验证选项 |
| 主节点 | 外部 Windows 客户端实际连接，查询出口与当前 VPS 匹配 |

## 当前真机通过

测试端口为专用临时资源。下表中的数字是本轮观察值，端口不是公开节点凭据，也不是用户部署时必须照抄的端口。

| 场景 | 操作与观察 | 判定边界 |
|---|---|---|
| 临时节点真实 TCP 业务 | 经 UDP/QUIC HY2 临时入口 `41000` 下载 4 MiB、上传 1 MiB，内容 SHA256 一致 | 同时证明 HY2 建连和双向实际数据传输，不只是端口监听 |
| UDP 转发 | 通过同一 HY2 客户端执行 UDP echo，响应内容正确 | 证明本轮 UDP 转发路径可用，不代表所有 UDP 应用或网络均通过 |
| 错误密码 | 错误凭据客户端退出 1，其本地代理请求 curl 退出 7 | 被拒绝，未建立可用代理 |
| 错误 SNI | 错误 SNI 客户端退出 1，其本地代理请求 curl 退出 7 | 保持正式 TLS 验证，未通过跳过验证绕过 |
| 来源 IP 槽位 | `IP_LIMIT=1` 时 Windows 外部来源已占位；VPS 回环第二来源被拒绝；改为 `IP_LIMIT=2` 后该第二来源允许 | 真实不同来源地址与内核规则通过；不是第二台独立公网设备的多用户并发测试 |
| 配额真实耗尽 | 5.12 MiB 配额通过真实下载耗尽，curl 退出 28，审计 `STATE=exhausted`、使用率 100% | 不以手改已用量模拟耗尽；下载超时本身需结合配额状态判断 |
| 配额重设恢复 | `pq_keepcycle.sh` 重设为 102.4 MiB，真实传输重新通过 SHA256 与 UDP echo 检查 | 已证明重设后服务可用；跨 30 天自动触发仍未验证 |
| 整端口暂停 | 对 `41000` pause，外部 TCP 请求得到 curl 状态 `000`，同端口 HY2 连接失败；相邻 `41001` TCP 控制请求仍为 200 | 暂停覆盖同数字端口的 TCP + UDP；不影响相邻控制端口 |
| 黑名单与暂停独立 | 对真实客户端来源添加 `/32` ban 后 resume，状态为 0 paused / 1 ban，TCP 与 HY2 仍阻断；clear 后恢复 | 证明解除端口暂停不绕过来源封禁；当前 `/24` 实测另见下项 |
| 真实来源 CIDR | 对 `41000` 封禁 Windows 来源所属 `/24` 后 pause / resume，状态仍为 0 paused / 1 ban；本端口 TCP HTTP 为 `000`、HY2 curl 退出 7，相邻 `41001` TCP 为 200；clear 后恢复 | 当前 VPS 的真实来源网段测试通过，不公开来源地址或实际网段 |
| portbw 首次集成 | 安装、verify、audit 通过；`41000` 静态 10 / 10 Mbps 的 nft / tc 状态均为 OK | 程序与安装器保持 `jieshu` 同源码；规则覆盖 TCP + UDP、IPv4 + IPv6，但本轮没有 IPv6 真实连接 |
| 限速下实际数据 | 同端口 TCP 4 MiB 下载观察到 `1,076,267 bytes/s`；HY2 双向内容 SHA256 与 UDP echo 均通过 | 是受限端口集成与吞吐观察，不声明每一瞬间精确等于 10 Mbps，也未独立量化 HY2 的 UDP 极限吞吐 |
| 真正系统重启 | 执行 `systemctl reboot` 后 SSH 重新连接成功；主节点、临时节点、guard、traffic、portbw 组件均 active | 实际整机重启，不是只重启单个服务；不是异常断电 |
| 重启后防护 | guard 的 1 paused / 1 ban 与 portbw 限速策略均恢复 | 证明配置与内核恢复；随后专项测试仍需安全清理 |
| 每日统计持久化 | 重启前后 DOWN=`23190783`、UP=`3569219` 字节精确一致 | 本次正常重启中没有观察到已保存统计丢失或重复累计；不证明突然断电尾部数据不丢失 |
| 配额持久化 | 重启前后 `SAVED_USED_BYTES=15823213` 精确一致 | 证明正常保存/恢复路径，不能延伸为任意异常断电结果 |
| Watchdog 受控故障恢复 | 主动 stop 专用临时节点，观察 `inactive`；运行 watchdog 退出 0，节点恢复 `active`；外部 SHA256 与 UDP echo 再次通过 | 真实停止与修复通过；不等于连续三次失败后的完整 72 小时宽限已验收 |
| 删除与端口复用 | 对 `41000` 同时配置 pause、ban、portbw 后执行节点清理，退出 0；节点元数据、限速策略、手工 guard 记录全部清除，随后同端口重建成功 | 证明受管理节点清理能解除归属本节点的残留；自然到期另见下项 |
| 手工 guard 表失效恢复 | 只删除 HY2 手工 guard 专用表，运行 watchdog 后暂停规则恢复 | 证明该专用表的恢复路径；没有清空整机 nft ruleset |
| 配额/IP 表失效恢复 | 删除 HY2 配额与 IP 限制两张专用表，watchdog 重建防护 | 当次为已用量 0 的新节点，只证明规则/状态恢复；不宣称丢表时未保存的字节没有丢失 |
| guard 工具丢失时安全停止 | 临时隐藏 guard CLI，watchdog 退出 1，主节点与临时节点均 `inactive`，节点元数据保留 | 证明无法核实手工暂停/黑名单时安全阻断，而不是继续无防护服务 |
| guard 工具恢复后重启业务 | 归还 CLI、restore 防护，手动 start 主节点，由 watchdog 恢复临时节点；外部 SHA256 与 UDP echo 通过 | 主节点需要显式重新启动，不把该场景描述为所有服务均自动恢复 |
| 自然 TTL 到期 | 创建 `D=90` 秒、端口 `41010` 专用节点，真实等待到期；元数据、portbw 策略、guard 记录自动清理，guard audit 为 0 paused / 0 ban | 正常自然到期通过，不以提前强制删除代替到期验收 |
| 可选 loopback Stats API 审计 | 在可丢弃普通节点上配置回环 API 与 root 权限 600 的 secret，真实客户端传输期间 `hy2-abuse` 读出 `online_client_instances=1`、`active_tcp_streams=1`，`target_counts` 非空 | 实际只读 API 联调通过；不公开认证值、目标内容或来源，不推导历史/DNS/UDP目标 |

## 当前 WG-NAT 真实联调

用户提供现有生产 NAT 的连接条件，并明确授权临时追加一枚独立 `/32` Peer、完成后清理。操作未运行 NAT `init`，未重启生产 WireGuard，未更改既有 Peer；核对生产 WG uptime 和原有两枚 Peer 的 AllowedIPs 均未改变。追加测试 Peer 前设置了 **1 小时自动清理 timer**。测试 VPS 端成功部署 WireGuard 与 `natjichang`。

| 场景 | 当前实际结果 | 边界 |
|---|---|---|
| Windows 外部 NAT 节点出口 | 经 HY2 NAT 临时节点查询出口，与授权 NAT 出口匹配 | 这是当前新 VPS、新 Peer 的真实结果，独立于旧机记录 |
| 真实下载 | 从独立公共诊断目标下载 102400 字节，SHA256 正确 | 不只是本机/WG 握手状态检查 |
| 真实上传 | POST 65536 字节，外部回显内容一致 | 验证双向业务数据 |
| QUIC 中 UDP 转发 | 通过 HY2 UDP 转发获得正确 DNS 响应 | 独立验证 HY2 UDP 业务经 WG-NAT 出口 |
| 停止测试 VPS WG | 停止本机 `wg-quick` 后 table 100 仍保留 `prohibit default metric 42760`，带 mark 的 `ip route get` 退出 2；NAT 客户端 curl 退出 7，普通主节点客户端仍退出 0 | NAT 节点安全断流、未改走 VPS 公网；主节点仍可用；生产 NAT 未停止或重启 |
| WG 重启等待握手 | 重启测试 VPS WG 后，握手尚未就绪时 watchdog 退出 1、拒绝启动 NAT 节点；真实握手就绪后 watchdog 退出 0、临时节点 active | 安全拒绝是预期启动顺序，不冒充始终在线 |
| 恢复后的真实业务 | 外部下载 SHA256、上传回显及 UDP DNS 再次全部通过 | 证明当前 NAT 节点真正恢复业务，而非仅 service active |

**保留的失败尝试：** 第一次选用了同一测试 VPS 公网地址上的本地 echo 目标。该目标不适合强制 `bindDevice` 到 WG 的 NAT 路径，请求 curl 退出 28；改用独立公共诊断目标后上述下载、上传与 UDP 检查通过。此失败记录不能解释为 WG-NAT 已被证明失效，也不从记录中删除。

**生产临时测试资源已清理并核实：** 恢复脚本断言 `CONFIG_EXACTLY_RESTORED=PASS`，原两枚 Peer 映射完全一致，WireGuard active 且 `ActiveEnterTimestampMonotonic` 与操作前相同，表明全程没有重启生产 WG。测试的一小时清理 timer 已 inactive，root 私有临时 helper 与备份目录已删除；测试 VPS 的 NAT 临时节点清理退出 0。生产环境当前没有本轮测试残留。本轮没有生产 NAT 机重启或异常断电测试。

### 配置 NAT 后的第二次真实整机重启：外部业务恢复通过

本轮再次真实 reboot 测试 VPS，保留普通和 NAT 两类节点。重连后 SSH、主节点、普通节点与 WG 服务均正常；NAT 每日统计重启前后 DOWN=`653509`、UP=`302685`，合计 `956194` 字节精确一致，配额 `SAVED_USED_BYTES=956194` 也精确一致。

刚重新连接时 NAT 服务处于 `activating`，Peer 尚未完成真实握手，客户端被拒绝，符合 fail-closed 启动顺序。随后真实握手就绪，watchdog 退出 0，NAT 服务 active，healthcheck 出口正确；Windows 外部客户端最后一轮下载、上传和 UDP DNS 均退出 0，下载 SHA256 正确、上传回显一致、DNS 响应正确。**本次重启的精确字节持久化、握手前安全拒绝及握手后外部业务恢复通过。** 生产 NAT 未重启。

## 卸载重装：两处真实缺陷修复后，保留数据链路复测通过

以下保留前两次真实失败及根因；之后重新执行完整保留数据链路并通过，未把先前的失败步骤直接改写成成功。

1. 卸载默认预览退出 0，安装状态未改变。
2. `hy2-uninstall.sh --yes` 退出 0：节点元数据、配置和证书仍保留；SSH 正常、portbw 仍 active；HY2 四张专用 nft 表无残留。此时完成的是“移除管理器与服务、保留数据”，未证明重装后节点恢复。
3. 首次重装主节点失败：旧主节点状态文件仍存在、服务 unit 已卸载；acme.sh 安装证书时立即调用 reload hook，旧逻辑将尚未重建 unit 的合法重装过程当作恢复故障。这是新增卸载路径暴露的真实兼容问题。
4. 修复证书 reload 时序并补充 5 项回归后，再次重装主节点退出 0、服务 active。此项修复的本机结果通过，不能据此宣称所有临时节点都恢复。
5. 随后发现临时节点仍有问题：保留元数据但 unit 缺失时，GC 将它误判为残留，影响保留数据的重建恢复。**当次整个保留数据卸载/重装链路未通过**，继续修复 unit 备份/恢复、GC 顺序以及 guard / NAT helper 保留。

**修复后完整复测：当前普通 + NAT 两节点保留数据卸载/重装通过。**

| 步骤 | 本轮实际结果 |
|---|---|
| 修复版保留数据卸载 | `--yes` 退出 0；普通与 NAT 两个临时 unit 各有权限 600 的备份；guard CLI / unit 与 NAT preflight helper 保留；SSH、WG、portbw 均 active |
| 重新安装 | manager 退出 0、主节点部署退出 0、每日统计安装退出 0；主节点、普通临时节点、NAT 临时节点全部 active |
| 防护恢复 | 原 guard 状态 1 paused / 1 ban 恢复；先恢复防护，再启动保留节点 |
| 共享策略隔离 | 本节点 portbw `41000=10/10` 保留；无关端口 `41001=20/20` 同样保留 |
| 健康检查 | doctor 为 0 error / 1 warning；警告为尚未固定核心 SHA256，不是被忽略的运行错误 |
| 恢复后客户端 | resume / clear 后，Windows 主节点出口核对通过；普通节点 4 MiB 下载 / 1 MiB 上传 SHA256 及 UDP echo 通过；NAT 节点外部 100 KiB 下载 SHA256、64 KiB 上传回显及 UDP DNS 再次全部通过 |

**证书 reload hook 实际调用通过：** 执行已注册的 `/usr/local/lib/hy2/acme-reload.sh`，退出 0，主节点和两类临时节点保持 active；随后再次完成上述外部客户端检查。这是当前真实服务上的 reload hook 回归，**不是 CA 实际续期、证书到期轮换或重新签证的证明**。

**清理数据、核心删除及重新安装也已实际通过：**

- `hy2-uninstall.sh --yes --purge --remove-core` 退出 0；`/var/lib/hy2`、HY2 env、Hysteria 核心及主节点链接移除，四张 HY2 专用 nft 表无残留。
- HY2 自有 `41000` 限速策略删除，无关 `41001` 策略保留；卸载当时 SSH、共享 portbw、WG 均 active，ACME 账户与工具保留。
- 随后 manager 安装退出 0，正式 TLS 主节点部署退出 0、服务 active；从已发布 `raw/main` 下载的 `hy2.sh` 与已验收源码逐字节 `cmp` 一致，`bash -n` 通过。

`/root/.acme.sh` 账户和 ACME 证书副本按设计保留，不将 HY2 purge 描述为删除全部系统密钥。最终主节点客户端与doctor已完成下节独立复验，没有把部署active代替客户端结论。

## 最终保留环境与复验

- purge后的主节点由Windows官方客户端真实连接，curl退出0，出口与当前测试VPS匹配。
- 每日统计、guard和审计可选工具重新安装；主节点、看门狗timer、traffic timer及guard service均active。临时节点元数据为0，guard audit为0 paused / 0 ban，portbw audit为空策略。
- UDP/443为唯一HY2监听；测试端口41000、41001、41002及临时Stats API端口17111均无监听。最终生产NAT再次只读核查为原两枚Peer、WG active、cleanup timer inactive、测试目录无残留；本机仅保留主节点与可选工具。
- 从官方当前版本发布信息取得[Hysteria 2.14.0校验清单](https://github.com/HyNetworks/hysteria/releases/download/app/v2.14.0/hashes.txt)。安装的Linux amd64核心SHA256为 `fc25edff9948708cb00a4ff01f3bccde677660aca050133bb1ad46c6860362d2`，与官方 `build/hysteria-linux-amd64` 完全相同；比对成功后才写入服务器 `HYSTERIA_BINARY_SHA256`。
- 最终 `hy2_doctor.sh --strict` 为 **0错误 / 0警告**，`hy2-abuse 443 --json`退出0。早先未固定核心SHA造成的1 warning为当时实际结果，保留在keep复测记录中。

## 功能对标汇总

| `jieshu` 适用能力 | HY2 实现与当前证据 | 结论边界 |
|---|---|---|
| 安装 / 更新管理器 | 全新管理器、正式 TLS 主节点与已发布源码一致性检查通过 | 本轮 Debian 13.5，不推广为所有发行版通过 |
| 卸载 / 保留恢复 / 重新安装 | 默认预览、keep 普通/NAT节点恢复、purge/core移除与重新安装通过 | 两处真实重装缺陷已修复，失败历史保留；最终主节点客户端/doctor通过 |
| 主节点 / 临时节点 / 订阅 | 主、普通临时、NAT临时节点真实客户端双向TCP/UDP通过；有凭据链接与订阅入口 | 不公开链接；订阅导入到所有客户端未逐一测试 |
| 总流量配额 / 手动重设 | 真实耗尽阻断、keepcycle重设恢复、正常重启精确计数保留通过 | 未实际等待30天；手工重设是清零重设，不是追加余额 |
| 每日流量 / 历史导出 | UDP独立计数、日统计与正常重启前后精确字节核对通过 | 跨午夜归属、30天裁剪及突然断电尾部计数未真机专项 |
| 来源IP限制 | 实际外部来源占位，回环第二来源拒绝/放行通过 | 不是第二台公网设备；槽位数不等于人数 |
| 暂停 / 黑名单 | 同端口TCP+UDP暂停、真实/32与/24、pause/resume与ban独立、重启持久化通过 | IPv6规则由自动化覆盖，本机没有真实IPv6客户端 |
| 端口静态限速 | 通用nft+tc安装、10/10策略、TCP吞吐及HY2业务、共享端口隔离通过 | 不要求瞬时吞吐精确等于配置上限 |
| 自动降速 / 保护 / 恢复 | portbw程序与安装器保持jieshu同源码，原算法真机证据可复用 | 本机没有重复持续高负载触发压测 |
| 节点删除 / 到期 / 端口复用 | 强制删除、90秒自然到期、配额/IP/guard/本端口portbw清理、端口重建通过 | CLI失败保留元数据与非零结果由回归覆盖 |
| WG-NAT / 防泄漏 | 当前新Peer真实出口、双向TCP/UDP、停测试WG阻断、握手及整机重启恢复通过 | 生产NAT未重启，原配置与Peer精确恢复无残留 |
| 服务 / 开机恢复 | 两次真实reboot，主/普通/NAT服务及计数/策略恢复通过 | 握手前安全拒绝是预期；最终保留环境为主节点 |
| 看门狗 / 异常处理 | 真正stop恢复、专用表恢复、guard CLI缺失安全停止/恢复通过 | 配额丢表测试已用0；完整72h与整机ruleset清空未测 |
| TLS / 证书钩子 / 核心管理 | 正式证书签发、错误SNI拒绝、注册reload hook及客户端通过，最终核心核对官方SHA256后固定 | 真实CA续期、跨版本及运行期失败升级回滚未测；SHA门禁拒绝回滚见接续结果 |
| 审计 / 日志 / 实时目标 | journal/source槽位入口与可选回环Stats API；实际读到在线1、TCP流1及非空目标汇总 | 不提供历史/UDP目标、实际人数或自动滥用定论 |
| 安全边界 / 共享组件 | 正式TLS验证、失败阻断、SSH保留、其他portbw策略/生产Peer不变通过 | 同机叠装VLESS完整管理器仍存在共享pq路径冲突，应分机部署 |
| VLESS Reality / SOCKS5专属 | HY2不复制Reality UUID/密钥或SOCKS5账号管理 | 不适用；HY2客户端本地代理端口不等于提供SOCKS5账号管理 |

## 直接复用的既有验收

- `portbw.py` 与 `portbw-install.sh` 保持和只读对标仓库完全相同的源码。自动降速、持续窗口、保护与恢复算法复用 `jieshu` 的既有真实上/下行触发结果。本轮补充了新 VPS 安装、nft/tc、TCP 与 HY2 使用及重启集成，**没有重复高负载自动触发测试，也不声称当前链路已完成该压测**。
- WG/NAT 公共机制参考[历史共享组件审计](SHARED_COMPONENT_AUDIT_2026-11-05.md)和[旧 HY2 真机记录](REAL_MACHINE_ACCEPTANCE_2026-11-04.md)。现有 NAT 继续沿用原管理器，未为 HY2 重装通用 NAT；本轮只新增经授权的临时独立 Peer，执行了上一节的新 VPS 出口、双向 TCP / UDP、断流与恢复联调，不把历史结果冒充当前结果。
- 仅源码、依赖和适用条件一致的公共实现可复用；Hysteria 的 UDP、QUIC、TLS 和本轮修改的状态管理不因“同源设计”自动算作通过。

## 自动化与文档检查

- 已推送阶段提交 [`0eedd49`](https://github.com/liucong552-art/hy2jieshu/commit/0eedd49)，[GitHub Actions run 43690417997](https://github.com/liucong552-art/hy2jieshu/actions/runs/43690417997) 成功。之后发现的重装缺陷由后续修复和上述完整真机复测验证，不能把早先 CI 当作后续修复的证据。
- 后续修复提交 [`432bf40`](https://github.com/liucong552-art/hy2jieshu/commit/432bf40) 已推送 `main`，包括保留节点重建和手工 guard 丢失时的安全停止等修复。
- [`432bf40` 的 GitHub Actions run 43692194673](https://github.com/liucong552-art/hy2jieshu/actions/runs/43692194673) 成功；其后4cc4faf对应CI run43693061619亦成功；新修复的CI按最终提交核对。
- 最新 Linux 测试快照为 **166 项测试通过**。它属于该次代码快照的自动化结果，不是 166 个独立真机功能，也不替代剩余实际故障与卸载测试。后续代码变化仍需最终回归。
- README 保留 `jieshu` 六章顺序、导航、折叠安装流程与完整命令；执行下载地址改为 `hy2jieshu`，历史来源记录保留在历史报告中。
- 新增独立卸载入口、文档链接/锚点/下载目标检查与对应回归。keep与purge/core删除两条路径分别完成真机执行及重装，最终主节点外部复验与doctor通过；4cc4faf对应CI亦成功；接续修复按最终提交核对。

## 当前待完成或缺少条件

| 项目 | 当前状态与下一步 |
|---|---|
| Watchdog 完整故障边界 | 本机主动 stop、guard 表恢复、guard 工具缺失时安全停止及归还后恢复通过；完整连续失败宽限仍未验证 |
| 自然到期与生命周期 | 主动删除、guard/portbw残留清除、同端口重建、真实 90 秒自然到期、普通/NAT节点保留数据重装恢复通过 |
| nft 防护失效与异常处理 | 手工 guard 表、配额/IP 表受控删除恢复已执行；配额表测试节点已用量为 0，不能推导未保存计数保护；整机规则未清空 |
| 卸载与重装 | 两次真实失败保留；keep完整恢复和purge/core删除/重新部署均通过；最终主节点外部客户端和严格doctor通过 |
| 当前 NAT 新机重启 | 第二次真实 reboot 后精确字节保留、安全拒绝、握手就绪后服务及Windows外部下载/上传/UDP全部通过 |
| 最终回归与文档CI | Linux166项测试、432bf40 CI通过；最终主节点客户端/doctor通过，4cc4faf CI亦成功，接续新增8项定向回归通过；最终提交CI按Actions核对 |
| 外部 WG/NAT | 本轮新Peer联调与重启恢复通过；生产配置精确恢复、原两Peer不变、临时Peer/timer/helper/备份无残留；生产NAT未重启 |
| HY2版NAT安装器 | 本轮生产机继续复用jieshu NAT，未执行/安装HY2 nat.sh；iputils-ping依赖与旧5参数兼容修复仅自动化通过，不等于新NAT机安装真机通过 |
| WG未来握手时间拒绝 | 主要由生成Bash边界回归覆盖并验证新机正常握手；本轮没有真机调时注入未来时间 |
| IPv6 | 当前测试VPS无全局IPv6、域名无AAAA，无法完成真实IPv6连接验收 |
| 72 小时宽限 / 30 天周期 | 未实际等待完整长周期；单测和历史锚点检查不能冒充长期执行 |
| 真实续证 | 首次正式签发及注册的 reload hook 真正调用后服务/客户端通过；尚未实际跨到期续证或 CA 真实轮换 |
| 核心升级失败回滚 | 接续已完成真实SHA不符候选拒绝、原核心及配置/凭据恢复、主节点自动恢复；跨版本及运行期失败回滚未测 |
| 异常断电 | 本轮仅正常 reboot，不宣称突然掉电持久化已通过 |
| 协议专属模块 | VLESS Reality 的 UUID / 密钥、SOCKS5 账号管理不适用于 HY2，不机械复制 |

## 保护与交接

验收后主动移除测试 VPS 上无关 `41001` 测试策略，停止/禁用测试 WG 接口及 timer。测试 WG 配置、env与密钥材料仅归档到root私有验收目录，不在服务器留下失效Peer状态反复触发doctor；测试Stats secret已删除。生产NAT已精确恢复且无测试残留。最终仅保留正式主节点与可选管理工具，最后客户端、审计和严格doctor均通过。

原始部署及客户端日志、节点配置、订阅和所有私钥保留在操作者私有环境，不提交到 Git。测试器与报告不保存真实来源 IP 或服务器公网地址。此记录继续按实际执行结果更新；接手者先读 [TASK_PROGRESS.md](../TASK_PROGRESS.md)、最近提交和本记录，再确认机器实际状态，避免重复已经通过且代码未变化的项目。

## 保存时的补充交接

- 本轮修改及新增文件已做敏感信息排查；不提交原始私有日志、真实凭据或节点链接。
- 额外系统观察：测试 VPS 的 networking.service 因尝试启用不存在的 eth1 而失败；当前 eth0 默认路由、SSH 与 HY2 客户端均正常。当时未改动或重启网络服务；接续已安全修复并验证失败unit为0，详见后文。
- 按用户额度要求停止扩展工作；长期与未验证项保持上文状态，生产服务器不再执行写操作。

## 接续核查与网络配置修复

- `4cc4fafa6952473f3c898a3e0f46106fe947e76f`本地与远程一致，工作区干净；[对应CI run43693061619](https://github.com/liucong552-art/hy2jieshu/actions/runs/43693061619)成功。既有166项与真机结果保留，未重复旧验收。
- 网络故障已定位：镜像配置含`auto eth1`和`iface eth1 inet dhcp`，真实链路只有lo/eth0；日志显示eth0获取地址成功，eth1报不存在。HY2脚本不写该配置。
- 备份原文件后仅移除上述两行。核对ifupdown状态及两种`--no-act`预演，确认活动接口不会重新配置，才对原failed oneshot执行一次`systemctl start networking.service`；未stop/restart/ifdown/force，也未重启系统。
- 前后eth0配置、实际地址、默认路由一致；独立新SSH连接成功，networking、HY2和timer均active，systemd失败unit数0。此为测试机镜像配置维护，不将网络改写加入HY2安装器。
- 生产机未再次连接。README仅纠正SSH端口共用风险说明，TCP/UDP双协议功能保持。
- 该阶段发现回滚吞错和删除备份问题；后续失败历史、修复与最终通过依据见下节。
- 补充首轮实际结果保留：修复快照172项Linux测试通过。官方核心副本附加不执行的尾部标记，候选仍可运行但SHA不同；真实部署到达SHA拒绝门禁，内层原核心恢复验证成功，外层恢复仍失败且保留原始备份，主节点未自动启动。因此此轮判定FAIL。操作者立即通过独立安全备份恢复官方核心并启动主节点，当前SHA正确、服务active；继续定位外层问题，不能用单测结果覆盖本次失败。

### 回滚补充最终结果

诊断复测保留了第二次FAIL：原核心和所有受保护文件已还原，但嵌套EXIT陷阱内的端口helper输出443却因裸return返回1，导致主节点未自动启动。独立安全恢复立即恢复服务。用真实common/port/EXIT调用链在Debian只读复现后，改为显式return0并补充对应回归。

最终必要复测PASS：使用当前已校验官方核心的副本，仅附加不执行的尾部标记；候选version成功、SHA不同。部署确实到达SHA拒绝门禁，实际拒绝SHA与候选一致；部署exit1符合预期。原官方核心SHA恢复，defaults、main.yaml、main.env、密码和主节点链接文件内容全部保持原样，主节点自动active，安全fallback timer已停用。随后Windows客户端curl0且出口正确；严格doctor0错误0警告，networking/HY2/timers active，systemd失败unit数0。测试VPS保存的入口脚本与修复源码一致。

新增8项隔离回归执行真实生成函数，覆盖恢复写回/哈希/配置/服务失败时备份保留和非零结果、成功恢复与清理，以及真实嵌套EXIT状态；另7项发布检查在Linux通过。早先完整172项快照保留为当时证据，最终变更由最终提交的Actions全量CI核对。本项只证明SHA拒绝后的真实回滚，不推导所有跨版本升级、运行期失败、磁盘故障或权限故障均已真机通过；这些错误的备份保留主要由隔离回归覆盖。
