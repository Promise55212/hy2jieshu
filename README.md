# HY2 / WG-NAT / 端口限速 / 可选 SOCKS5 落地

<!-- HY2-README-FULL-PARITY-2026-11-16: local docs only -->

<!-- HY2-README-FULL-PARITY-2026-11-16: local docs only -->

命令使用 **root + Bash**，示例端口换成实际端口。长命令和低频操作点击展开，所有内容都在本 README 内。

[查询](#queries) · [新建节点](#create) · [修改与重置](#modify) · [排查](#trouble-guide) · [封禁与删除](#remove) · [安装与更新](#install) · [卸载](#uninstall) · [验收](#acceptance)

> 对标 [jieshu README](https://github.com/liucong552-art/jieshu/blob/main/README.md) 的六章节顺序、查询入口和折叠布局，命令针对 Hysteria 2 的 UDP / QUIC / TLS 适配。当前验收见[验收与对标](#acceptance)，开发接续见 [TASK_PROGRESS.md](TASK_PROGRESS.md)。

<a id="queries"></a>
## 一、查询与检查

| 想查什么 | 在哪台机器 | 命令 |
|---|---|---|
| 主节点、临时节点、到期、配额、IP 占用 | HY2 VPS | `hy2_audit.sh` |
| 某端口配额归属、已用量、剩余量、重置周期 | HY2 VPS | `pq_audit.sh` |
| 端口监听、TLS、WG 出口和管理组件 | HY2 VPS | `hy2_doctor.sh --strict` |
| 指定临时节点状态 | HY2 VPS | `hy2_audit.sh --tag hy2-temp-节点名称` |
| 刷新临时节点订阅 | HY2 VPS | `hy2_temp_sub.sh` |
| WG 状态与握手（只读） | HY2 VPS | `wg show wg-nat`；主动出口与防护检查见 [WG-NAT](#wg-nat) |
| Peer 列表 / NAT 出口机状态 | NAT 机 | `bash /root/nat.sh list` / `bash /root/nat.sh status` |
| 异常服务日志 | HY2 VPS | [故障排查](#troubleshooting) |
| 独立端口限速与自动降速（可选） | HY2 VPS | [安装与管理 portbw](#portbw) / `portbw report` | 
| 今天 / 指定端口每日流量 | HY2 VPS | `hy2_traffic` / `hy2_traffic 40020`（[先安装](#daily-install)） |
| 全部受管理暂停、IP/CIDR 黑名单 | HY2 VPS | `hy2-guard status` / `hy2-guard audit`（[先安装](#port-block)） |
| 节点链接、自动重置日期、自动降速日志 | HY2 VPS | [查链接](#node-link) / [查重置日期](#quota-reset-time) / [查限速日志](#speed-logs) |
| SOCKS5 账号、到期、剩余配额与 IP 占用 | 独立 SOCKS5 落地机 | `socks5 list`（[手动安装](#socks5)） |
| SOCKS5 链接、每日用量与使用审计 | 独立 SOCKS5 落地机 | [查询说明](#socks5-query) |

`hy2_audit.sh` 和 `pq_audit.sh` 对同一端口的配额使用同一底层计数快照，不是两套不同计费。`hy2_temp_sub.sh` 输出的订阅文件包含节点凭据。

**阅读与使用方式：** 先使用本章总览取得节点/配额/状态，再选择对应折叠章节；不可把 `pq_audit.sh` 的配额余额当成当日统计，也不可把 `portbw report` 的 Mbps 当成总流量。端口是管理入口，节点凭据、Peer 私钥及原始日志不应外传。下方命令中 `40020`、`41004` 等数字均为示例，执行修改类命令前先查真实端口与归属。

| 需求 | 首选入口 | 补充入口 | 注意事项 |
|---|---|---|---|
| HY2 主/临时节点、有效期、配额/IP 槽位 | `hy2_audit.sh` | `pq_audit.sh`、`hy2-guard status` | `IP_LIMIT=0` 不建立占位记录，不能据此断言无人访问 |
| HY2 错误日志与当前 TCP 目的地 | `hy2-abuse 40020 --days 7` | 开启回环 Stats API 后带 `--stats-url` | 不是完整历史域名审计，也不包含 UDP 历史目标 |
| SOCKS5 账号、到期与访问历史 | **落地机** `socks5 list` | `socks5 access 41004 7` | 与 HY2 完全独立、仅 TCP CONNECT |
| WG-NAT Peer 与出口 | **NAT 机** `bash /root/nat.sh list` | HY2 VPS `wg show wg-nat` | 只读状态不等于外部真实出口测试 |
| 带宽限制与保护 | `portbw report` | `portbw auto status 40020` | TCP/UDP 共用端口限额，升级和恢复另有独立流程 |

<details><summary>展开：已有的审计、主节点和临时节点订阅命令</summary>

#### 查看全部节点

```bash
hy2_audit.sh
```

#### 综合健康检查

```bash
hy2_doctor.sh --strict
```

也可以执行：

```bash
bash /root/hy2.sh doctor
bash /root/hy2.sh version
```

#### 重新生成临时节点订阅

```bash
hy2_temp_sub.sh
```

单节点链接保存在 `/var/lib/hy2/temp/<完整TAG>.url`，主节点链接在 `/root/hy2_main_url.txt`。这些链接含密码，请勿粘贴到公开日志或 GitHub。

</details>

<a id="advanced-queries"></a>

<details>

<summary>补充查询：只在总览未提供所需信息时使用</summary>

| 查询 | 命令 | 说明 |
|---|---|---|
| 所有受管理配额 | `pq_audit.sh` | 显示配额归属及周期 |
| 单节点 | `hy2_audit.sh --tag hy2-temp-节点名称` | 到期与状态 |
| 单端口限速 | `portbw show 40020` | 独立的 nft/tc 状态 |
| 动态限速采样进度 | `portbw auto status 40020` | 触发、保护与恢复 |
| 限速自检 | `portbw audit` | 异常返回非零 |
| NAT 状态 | `wg show wg-nat` | 只读查看 Peer 与握手；实际出口需主动检查 |

累计总流量配额和 Mbps 带宽是不同概念。

</details>

<a id="node-link"></a>

<details>

<summary>按端口查询 HY2 节点链接</summary>

修改第一行端口。输出包含密码，不要提交到 GitHub。

```bash
PORT=40020
if [[ "$PORT" == 443 ]]; then
  cat /root/hy2_main_url.txt
else
  mapfile -t m < <(grep -l "^PORT=$PORT$" /var/lib/hy2/temp/*.env 2>/dev/null)
  if (( ${#m[@]} == 1 )); then
    cat "${m[0]%.env}.url"
  else
    echo "未找到唯一端口对应的节点，请检查 hy2_audit.sh"
  fi
fi

```

</details>

<a id="active-ips"></a>

<details>

<summary>查看来源 IP 占位与 UDP 监听</summary>

`IP_LIMIT` 为活跃来源 IP 槽位，不是实际人数；HY2 用 UDP，不照搬 VLESS 的 TCP established 查询。

```bash
PORT=40020
source /usr/local/lib/hy2/iplimit-lib.sh
hy2_il_active_ips "$PORT"
ss -lunp | grep ":$PORT " || true

```

</details>

<a id="daily-traffic"></a>

<details>
<summary>HY2 每日流量：今天、单端口最近 30 天、历史 JSON 导出</summary>

**已实现独立可选组件**：从 `jieshu/traffic.py` 移植到 HY2 的 UDP 计数器、密码身份及主节点 `MAIN_PORT`。按北京时间自然日保存最近 30 天，`UP` 用户上传、`DOWN` 用户下载、`TOTAL` 当日合计；这是**独立的每日历史**，与 `pq_audit.sh` 的双向总配额互不冲突。必须先按 [6.3 安装每日流量](#daily-install)，安装前的历史流量无法补记。

```bash
# 所有当前节点今天的上传、下载
hy2_traffic

# 指定临时节点最近 30 天
hy2_traffic 40020

# 主节点最近 30 天
hy2_traffic main

# 按临时节点 ID 或完整 TAG
hy2_traffic nat4
hy2_traffic hy2-temp-nat4

# 导出指定端口仍保留的每日历史 JSON（字节）
hy2_traffic 40020 --json
```

- 数据文件 `/var/lib/hy2/traffic/daily.json`，节点密码不保存到历史文件，只保存不可逆身份摘要；同名重建/端口复用、主节点密码轮换不会继承旧用户历史。
- 每分钟定时采集；查询时也执行采集。自动删除/到期节点的历史会在下次成功采集时清理，保留 30 个北京时间自然日。
- 采用**独立** `inet hy2_daily_traffic` nft 表，只统计该节点 UDP 端口双向字节，不修改 `hy2_pq` 或 `hy2_iplimit`。跨午夜分钟采样、断电尚未保存的尾部流量有少量归属/丢失风险，不能把它作为毫秒级结算系统。
- 与 `jieshu` 一样配有定时采集和关机 `ExecStop` 保存服务。旧测试机已有实际读写及正常重启保留记录；当前新机结论单独记录在[本轮验收](#acceptance)，CI 不能代替真机。

</details>

<a id="speed-logs"></a>

<details>
<summary>自动限速日志：全部端口、单端口、全部尚存历史</summary>

以下依次查询：最近 24 小时全部端口、最近 24 小时指定端口、指定端口全部尚存历史。北京时间输出；旧日志不代表当前配置，当前值以 `portbw report` 为准。

up / down 分别为上传 / 下载；没有自动降速日志不代表基础限速失效。可查历史受 journald 轮替、容量和保留策略限制。

```bash
TZ=Asia/Shanghai journalctl -u portbw-watch.service \
  --since '24 hours ago' --no-pager -o short-iso \
  | grep -E '自动降速|恢复基础速度|失败|Error|Traceback' \
  || echo '最近24小时没有匹配的降速、恢复或报错日志'
```

```bash
PORT=40002
TZ=Asia/Shanghai journalctl -u portbw-watch.service \
  --since '24 hours ago' --no-pager -o short-iso \
  | grep -E "${PORT} (up|down): (自动降速|恢复基础速度)" \
  || echo "最近24小时端口 ${PORT} 没有降速或恢复记录"
```

```bash
PORT=40002
TZ=Asia/Shanghai journalctl -u portbw-watch.service \
  --no-pager -o short-iso \
  | grep -E "${PORT} (up|down): (自动降速|恢复基础速度)" \
  || echo "端口 ${PORT} 没有尚存的降速或恢复历史记录"
```

</details>



<a id="hy2-audit"></a>

### HY2 来源 IP、连接错误与访问目标审计

**现已提供可执行的只读工具 `hy2-abuse.py`**，专门针对 HY2，而不是把 `vless-abuse` 改名。直接从受管理的 HY2 临时节点/IP 槽位，以及该节点的 `journalctl` 提取已有证据：

```bash
PORT=40020 DAYS=7 hy2-abuse
hy2-abuse 40020 --days 7 --json
```

- **当前来源 IP**：从 HY2 nftables `hy2_iplimit` 集合读取活跃槽位。若 `IP_LIMIT=0`，没有此类占位记录，**不能**据此认定“没有用户”。
- **异常事件**：从该 HY2 systemd 服务最多扫描最近 3000 条 journald 消息，按认证、握手、QUIC、超时、网络等类型统计警告/错误；不会在报告中输出原始错误字符串或节点密码。日志被轮替、事件未记录时无法补查。
- **实时访问目标**：如果手动配置了 Hysteria 2 **Traffic Stats API** 且仅绑定回环地址，可额外查询**当前 TCP 流**的目标地址、当前在线实例数（见安装说明）。**UDP 目标和历史目标列表不由该 API 提供**，不能虚构。
- **只读**：不触发自动封禁，也不更改配额、WG、nft 规则。IP 槽位/在线实例数不等于真实人数，出现异常事件也不等于已经确定滥用。

#### HY2 异常排查：按端口、日志类别与证据边界

审计工具只读已存在的日志与运行态，不安装持续记录历史域名的代理，也**不会自动识别滥用者**。与 `jieshu` 的审计入口保持相同的“先查询、后判断”体验；采集机制仍遵循 Hysteria2 实际能力。

| 想知道什么 | HY2 VPS 的查询方式 | 能得出的结论 |
|---|---|---|
| 某端口最近 7 天是否有认证/握手错误 | `hy2-abuse 40020 --days 7` | 在仍保留的 journald 样本中按类别统计错误/警告，不是全部连接记录 |
| 是否有特定来源 IP 正占用槽位 | `hy2-abuse 40020 --days 7 --json` | 只有启用 IP 槽位限制且对应集合存在，才有当前占位信息 |
| 主节点本身的服务日志 | `journalctl -u hy2.service --since '24 hours ago' --no-pager` | 可能含有敏感字段；**不应公开原始日志** |
| 当前 TCP 流量访问目标 | 先自行按 [Stats API 说明](#abuse-install)启用回环 API，再用 `--stats-url` | 当前 TCP 流，不能推导完整历史、UDP 目标或真实人数 |
| 是否另有整端口暂停/来源封禁 | `hy2-guard status` / `hy2-guard audit` | 手工防护规则，与访问日志不是同一个数据源 |

`--days 7` 的时间范围只约束 journal 查询；最多读取该服务最近 3000 条日志。超过范围、被 logrotate 清理或从未被记录的历史信息，不能通过修改天数追回。`auth`、`handshake`、`quic`、`timeout` 等类别代表事件类型，不代表某来源一定恶意；统计结果不能替代手工证据分析。

需要按端口识别具体临时服务时，先使用 `hy2_audit.sh` 获取完整 TAG，再查询相应 `hy2-temp-...service` 的 journal。不要用 `ss -ltn` 的 TCP 监听结论判定 HY2 UDP/443 是否在线，也不要把 NAT 出口目标地址误当作用户来源。

<a id="subscription"></a>

<details>

<summary>导出有效临时节点订阅（生成文件）</summary>

只导出有效且运行的临时节点到 `/root/hy2_temp_subscription.txt` 和 Base64 文件，不包含主节点。Base64 不是加密。

```bash
hy2_temp_sub.sh

```

</details>

<a id="socks5-query"></a>

<details>
<summary>可选 SOCKS5 落地：账号、每日流量与访问审计</summary>

以下仅在[独立安装 SOCKS5](#socks5)的落地机执行，与 HY2 的 UDP 配额、IP 槽位和每日统计分别管理：

```bash
socks5 list
socks5 link 41004
socks5 quota 41004
socks5 ip-show 41004
socks5 status
socks5 audit 41004
```

`LIMIT / USED / LEFT` 为账号总配额、已用与剩余，`TTL` 为有效期，来源 IP 槽位不等于人数；未知或读取失败不能当成零。需要完整账号凭据时才运行 `socks5 show 41004 --credentials`，不要公开输出。

<a id="socks5-daily"></a>

#### SOCKS5 每日流量：今天与最近 30 天

每日流量需先按[6.5](#socks5)开启采集；约每分钟采样，按北京时间保留最近 30 天，不等于实时配额余额：

```bash
socks5-traffic
socks5-traffic 41004
socks5-traffic 41004 --json
```

<a id="socks5-access"></a>

#### SOCKS5 使用审计、共享和异常连接

访问审计按成功连接、原始主机名和各实例 journal 统计；日志通常在连接结束时写入，直接连接 IP 时不能推断域名，缺失或已清理的历史无法补查。天数范围 1～90：

```bash
socks5 access 41004 7
socks5 access-domains 41004 7
socks5 access-errors 41004 7
socks5 access-errors 41004 7 --limit 200
socks5 access-errors 41004 7 --all
```

`access` 提供概览，`access-domains` 列出全部成功连接的原始域名，`access-errors` 统计非零错误并列出明细；`--limit` 只改变明细条数。当前 TCP 连接与历史成功记录含义不同，不能把连接次数、来源 IP 或错误码直接当作人数、网页访问次数或恶意行为。

**SOCKS5 查询字段速查（所有命令仅在独立落地机执行）：**

| 需求 | 命令 | 特别注意 |
|---|---|---|
| 按端口看链接 | `socks5 link 41004` | 可能包含凭据，不能转发公开群组 |
| 查询余额和到期 | `socks5 list` | `LIMIT / USED / LEFT` 是合计流量，不是单向限额 |
| 当前源 IP 占位 | `socks5 ip-show 41004` | IP 不是实际用户数；槽位超时释放不强制断开已有 TCP |
| 查看某端口精确配额 | `socks5 quota 41004` | 不要误认为是每日统计 |
| 当前服务和规则自检 | `socks5 status` / `socks5 audit 41004` | 不是访问域名历史查询 |
| 过去 7 天访问域名和异常连接 | `socks5 access 41004 7` | 来自已有代理日志；原始日志若缺失无法补查 |
| 列出全部已记录的成功访问域名 | `socks5 access-domains 41004 7` | 直接按 IP 连接时不能推导一个域名 |
| 查询错误码明细 | `socks5 access-errors 41004 7 --all` | 错误不等同于已经证实滥用 |

日志与凭据属于敏感信息，应留在落地机的 root 私有环境。业务运行期间不要为了补齐历史日志而重装、重启现有 SOCKS5 服务。

</details>

<a id="create"></a>

## 二、新建节点

<a id="temp-create"></a>

### HY2 临时节点

在 **HY2 VPS** 执行。下面两种命令二选一：示例有效期 7 天，总配额 50 GiB，最多 3 个活跃来源 IP；WG-NAT 命令需先完成[WG-NAT 部署](#wg-nat)。

普通临时节点：

```bash
DAYS=7; IP_VERSION=4 IP_LIMIT=3 PQ_GIB=50 D=$((DAYS*24*60*60)) hy2_mktemp.sh
```

WG-NAT 临时节点：

```bash
DAYS=7; IP_VERSION=4 IP_LIMIT=3 PQ_GIB=50 D=$((DAYS*24*60*60)) hy2_mktemp_nat.sh
```

<details>
<summary>其他创建方式：分钟、小时、固定端口、IPv6</summary>

### 按分钟

普通临时节点：

```bash
MINUTES=30; IP_VERSION=4 IP_LIMIT=3 PQ_GIB=1 D=$((MINUTES*60)) hy2_mktemp.sh
```

WG-NAT 临时节点：

```bash
MINUTES=30; IP_VERSION=4 IP_LIMIT=3 PQ_GIB=1 D=$((MINUTES*60)) hy2_mktemp_nat.sh
```

### 按小时

普通临时节点：

```bash
HOURS=2; IP_VERSION=4 IP_LIMIT=3 PQ_GIB=1 D=$((HOURS*60*60)) hy2_mktemp.sh
```

WG-NAT 临时节点：

```bash
HOURS=2; IP_VERSION=4 IP_LIMIT=3 PQ_GIB=1 D=$((HOURS*60*60)) hy2_mktemp_nat.sh
```

### 固定端口

下面示例固定使用端口 `40000`，有效期为 1 小时。

普通临时节点：

```bash
HOURS=1; IP_VERSION=4 PORT_START=40000 PORT_END=40000 IP_LIMIT=3 PQ_GIB=1 D=$((HOURS*60*60)) hy2_mktemp.sh
```

WG-NAT 临时节点：

```bash
HOURS=1; IP_VERSION=4 PORT_START=40000 PORT_END=40000 IP_LIMIT=3 PQ_GIB=1 D=$((HOURS*60*60)) hy2_mktemp_nat.sh
```

固定端口时，`PORT_START` 和 `PORT_END` 必须设置为同一个端口。

### 创建 IPv6 入站节点

IPv6 只需改一个参数，按下面两步操作：

1. 在 `/etc/default/hy2-main` 中填写 `HY_IPV6_DOMAIN`，并确保该域名的 AAAA 记录指向当前 HY2 VPS。
2. 将上面任意创建命令中的 `IP_VERSION=4` 改成 `IP_VERSION=6`，其他参数不用改。

例如，创建 IPv6 临时节点：

```bash
HOURS=2; IP_VERSION=6 IP_LIMIT=3 PQ_GIB=1 D=$((HOURS*60*60)) hy2_mktemp.sh
```

WG-NAT 同样只需把 `IP_VERSION=4` 改成 `IP_VERSION=6`；客户端通过 IPv6 连接 HY2 VPS，出站仍是 NAT 机的公网 IPv4。

常用调整：

- 不限制来源 IP：改为 `IP_LIMIT=0`
- 不限制流量：删除 `PQ_GIB=...`
- 修改固定端口：同时修改 `PORT_START` 和 `PORT_END`

创建成功后会直接输出端口、到期时间和节点链接。

**创建后如何验收、如何选择类型：** 先用 `hy2_audit.sh` 查到新 TAG、真实端口、剩余 TTL 与配额/IP 限制，再从自己的兼容客户端连接；仅 `systemctl active`、UDP 监听或脚本输出链接并不能证明公网客户端可用。普通节点从 VPS 公网出站；NAT 节点必须先核实自己的 WireGuard Peer、握手、mark 路由与出口防泄漏，不能将其失败时自动改走 VPS 出口。

| 创建意图 | 使用命令 | 对创建结果的关键检查 |
|---|---|---|
| 普通 UDP/QUIC 临时节点 | `hy2_mktemp.sh` | 对外 UDP 端口、SNI/证书、密码、配额与 IP 槽位 |
| WG-NAT 临时节点 | `hy2_mktemp_nat.sh` | 以上条件，加上专属 Peer、WG 路由和真实 NAT 出口 |
| IPv6 入站 | 增加 `IP_VERSION=6` | VPS 有全局 IPv6、AAAA/SNI/防火墙与客户端 IPv6 均正确 |

禁止在已有真实业务端口上运行固定端口创建示例；`PORT_START=PORT_END` 只是指定端口，不是绕过端口冲突检测的办法。TTL 和 30 天配额周期是两个时间维度，修改配置不会自动延长节点到期时间。

</details>

<details>
<summary>创建参数、节点类型与自动重置规则</summary>

普通节点用 VPS 出口，WG-NAT 节点用 NAT 出口；`id` 可省略或填写英文 / 数字 / 点 / 下划线 / 连字符。

| 参数 | 含义 |
|---|---|
| `D` | 有效期秒数，由示例前面的分钟 / 小时 / 天数计算 |
| `PQ_GIB` | 上传+下载合计配额；不限量时省略，不能填 0 |
| `IP_LIMIT` | 活跃来源 IP 槽位数；0 为不限数量 |
| `IP_STICKY_SECONDS` | 闲置占位秒数，默认 120；持续访问会刷新 |
| `PORT_START` / `PORT_END` | 固定端口时两项填相同端口 |
| `IP_VERSION` | 入站协议族 4 / 6 |

创建时有配额且有效期严格超过 30 天，才每 30×24 小时自动重置；不是每月 1 日，重置也不延长有效期。

</details>

<a id="socks5-create"></a>

<details>
<summary>可选 SOCKS5：新建账号、固定端口与家宽公网映射</summary>

先在**独立落地机**按[6.5](#socks5)手动安装；HY2 安装器不自动安装此模块。以下按分钟、小时、天及指定端口分别给出可复制示例。示例只在**新建或明确选定的独立 SOCKS5 落地机**执行，不在 HY2 入口机执行。

#### 创建 30 分钟账号

来源 IP 上限 1、闲置占位 60 秒、双向合计 1 GiB 配额：

```bash
MINUTES=30; IP_LIMIT=1 IP_STICKY_SECONDS=60 PQ_GIB=1 D=$((MINUTES*60)) socks5 add
```

#### 创建 2 小时账号

来源 IP 上限 2、闲置占位 300 秒、合计 5 GiB 配额：

```bash
HOURS=2; IP_LIMIT=2 IP_STICKY_SECONDS=300 PQ_GIB=5 D=$((HOURS*3600)) socks5 add
```

#### 创建 7 天账号

来源 IP 上限 3、闲置占位 600 秒、合计 50 GiB 配额：

```bash
DAYS=7; IP_LIMIT=3 IP_STICKY_SECONDS=600 PQ_GIB=50 D=$((DAYS*86400)) socks5 add
```

#### 固定本机监听端口

创建监听 `41004` 的 1 小时账号；省略 `PORT` 则由安装器选择本机空闲端口：

```bash
HOURS=1; IP_LIMIT=1 IP_STICKY_SECONDS=60 PQ_GIB=1 PORT=41004 D=$((HOURS*3600)) socks5 add
```


`IP_LIMIT=0` 不限来源 IP 数；省略 `PQ_GIB` 不限总流量，省略 `PORT` 自动选空闲端口。持续活动刷新来源占位时间，超时释放槽位不等于强制断开已建立连接。

**参数详细说明：**

| 参数 | 含义 | 适用说明 |
|---|---|---|
| `D` | 账号有效期，单位秒 | 可以由 `MINUTES`、`HOURS`、`DAYS` 变量计算；变量本身不是安装器子命令 |
| `IP_LIMIT` | 同时占用的来源 IP 槽位上限 | `0` 表示不限；不等于 TCP 会话数量 |
| `IP_STICKY_SECONDS` | 某来源 IP 闲置后释放名额的时间 | 活跃来源会刷新占位，不能据此保证强制踢出连接 |
| `PQ_GIB` | 合计上传+下载流量额度，GiB | 不设表示无总配额；配额在账号级累计 |
| `PORT` | 本机监听 TCP 端口 | 管理、配额、独立限速均按本机端口操作 |
| `--host` / `--public-port` | 客户端使用的公网域名和映射端口 | 不会替你创建路由器端口映射，需自行配置 TCP 映射 |

创建前先核对本机端口未被现有账号或其他服务占用；删除账号前核对 `socks5 list`，避免误删真实用户。原版 SOCKS5 不支持 UDP ASSOCIATE；即使与 HY2 同一仓库，也不代表它自动具备 UDP 代理能力。

家宽路由器需配置 **TCP** 公网端口映射；例如外部 `51004` 映射到本机 `41004`：

```bash
HOURS=1; IP_LIMIT=1 IP_STICKY_SECONDS=60 PORT=41004 D=$((HOURS*3600)) socks5 add --host proxy.example.com --public-port 51004
```

域名与外部端口换成真实值；后续管理及限速使用**本机监听端口 41004**。原样复用的版本仅支持 TCP CONNECT，不支持 UDP ASSOCIATE / BIND；没有新增 UDP 参数或转换 HY2 协议。

</details>

<a id="modify"></a>
## 三、修改与重置

<a id="quota-ip"></a>

### 配额与来源 IP

**重要：`pq_add.sh` 是重新设置整份配额，不是追加流量。** 修改已有临时节点会将已用量清零，不延长节点 TTL，也不启用 30 天自动重置。修改后立即执行 `pq_audit.sh` 核对。

#### 设置端口双向总流量

```bash
pq_add.sh 40000 50
```

表示 UDP `40000` 的上行与下行合计最多 `50 GiB`。

#### 查看全部配额

```bash
pq_audit.sh
```

#### 删除端口配额

```bash
pq_del.sh 40000
```

#### 设置活跃来源 IP 数量

```bash
ip_set.sh 40000 2 300
```

表示最多允许 2 个活跃来源 IP，每个槽位保持 300 秒。

#### 删除 IP 数量限制

```bash
ip_del.sh 40000
```

删除 IP 数量限制后，地址族隔离仍然保留。

临时节点到期或被删除时，其配额和 IP 限制也会一起清理。

### 准确输入 MiB 配额

`PQ_GIB` 与 `pq_add.sh` 的流量参数均为 GiB；**1 GiB = 1024 MiB**。

| 想要的额度 | GiB 参数 | 示例 |
|---|---|---|
| 50 MiB | `0.048828125` | `pq_add.sh 40020 0.048828125` |
| 100 MiB | `0.09765625` | `pq_add.sh 40020 0.09765625` |
| 500 MiB | `0.48828125` | `pq_add.sh 40020 0.48828125` |

`pq_del.sh` 与 `ip_del.sh` 仅取消对应限制，不删除临时节点；删除前请确认端口对应的节点身份。

<a id="quota-keep-cycle"></a>

### 手动重置流量并保留原自动重置日期

**已实现 `pq_keepcycle.sh`**：直接使用 HY2 现有的配额库、临时节点/配额双锁、nft 原子重建和元数据所有者检查。对**已有配额且尚未到期的临时节点**，将总配额重新设定、已用量清零，**保留原 30 天周期日期**；若有效期严格超过 30 天、但此前 `pq_add.sh` 清除了周期，可按节点创建时间恢复应有的周期锚点。短期节点不会新增周期。

**历史验收（2026-11-05，旧测试机）**：独立 31 天 HY2-NAT 临时节点已用 41.07KiB 时调用 `pq_keepcycle.sh`，配额 20.48MiB → 40.96MiB、已用清零、原 30 天重置时间（北京时间 2026-12-05 09:20:25）不变，`KEEP_CYCLE_METADATA_TEST=PASS`，主 HY2/WG 正常。实际跨 30 天自动触发仍未验证。

示例：把 UDP 40020 的配额重置为 **500 MiB**，保留或按创建日恢复原周期：

```bash
pq_audit.sh 40020
pq_keepcycle.sh 40020 0.48828125
pq_audit.sh 40020
```

如果你还没有重新运行新版 `hy2.sh` 管理器，也可**只下载独立命令**，避免重装 WG 或修改运行中的 HY2：

```bash
curl -fL https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/pq_keepcycle.sh -o /root/pq_keepcycle.sh
bash -n /root/pq_keepcycle.sh
bash /root/pq_keepcycle.sh 40020 0.48828125
```

执行会在 `/root/pq-keepcycle-端口-随机字符/` 下备份节点和配额元数据（含敏感信息，保持 root 私有），然后更新配额和 nft 规则。与 `pq_add.sh` 的关键区别是**不随手删除原自动重置日期**。必须确认端口正确，且确定需要将已用量清零；该命令不是增加余额。

**测试边界**：历史记录支持已用清零与周期锚点保留；实际跨 30 天触发不在该记录范围。新机与当前代码的验证状态见[本轮验收](#acceptance)。测试只能使用专用节点，正式业务端口上执行会清零已用量。

<a id="quota-reset-time"></a>

<details>

<summary>查询端口下次自动重置时间及倒计时（只读）</summary>

只需修改端口；此查询读取 `/var/lib/hy2/quota`，不会修改内核配额。

```bash
PORT=40020
META="/var/lib/hy2/quota/$PORT.env"
if [[ -f "$META" ]]; then
  NEXT=$(awk -F= '$1=="NEXT_RESET_EPOCH"{print $2; exit}' "$META")
  INT=$(awk -F= '$1=="RESET_INTERVAL_SECONDS"{print $2; exit}' "$META")
  if [[ "$NEXT" =~ ^[0-9]+$ && "$INT" =~ ^[0-9]+$ ]] && (( NEXT>0 && INT>0 )); then
    TZ=Asia/Shanghai date -d "@$NEXT" "+下次计划重置（北京时间）：%F %T"
    NOW=$(date +%s)
    (( NEXT>NOW )) && echo "剩余 $((NEXT-NOW)) 秒" || echo "已到预定时间，请检查 pq-reset.timer"
  else
    echo "该端口没有启用周期重置"
  fi
else
  echo "没有该端口配额配置"
fi

```

`pq-reset.timer` 开机约 15 分钟后首次检查，以后通常每小时检查一次。

**自动重置与手动修改的区别：** 对有效期严格超过 30 天且创建时有配额的临时节点，周期重置使用节点自己的锚点，通常每 30×24 小时计算一次，并不会在北京时间每月 1 日统一重置。重设额度可能导致 `pq_add.sh` 清除原周期，需按具体业务需求选择 `pq_keepcycle.sh`。此处的查询命令是只读的，`pq-save.timer` 保存累计用量，与自动重置定时器职责不同。

```bash
systemctl list-timers --all pq-reset.timer
journalctl -u pq-reset.service -n 50 --no-pager

```

</details>

<a id="quota-set-current-remaining"></a>

### 临时修改本期剩余流量（下周期恢复原配额）

与 `jieshu` 的[本期剩余额度一行调整](https://github.com/liucong552-art/jieshu/blob/f21b70d0f52f8f9cd6cbcc0a1fe4a8fd11b221fe/README.md#quota-set-current-remaining)对应，HY2 可以**直接复用已安装的 `/usr/local/lib/hy2/common.sh` 与 `quota-lib.sh`** 完成相同用途。不需要下载安装新脚本或重装 HY2；**此命令是 README 中的临时 Bash 操作，不代表仓库已有 `pq_set_remaining.sh` 可执行程序**。

适用范围：**已有有效 30 天自动重置周期、尚未到期、原始配额正常的 HY2 受管临时节点**。例如原始总额度 200 GiB，本期希望**从此刻起还可使用 85 GiB**，只修改最前面的 `PORT=40020` 与 `LEFT_GIB=85` 两个值，其他内容完整复制到该 HY2 VPS 的 **root Bash 终端**。如果是短期节点、没有周期的节点、已到下次重置时间附近（60 秒内）或配额状态异常，命令会拒绝修改。**务必先确认真实端口和账号归属。**

<details>
<summary>展开：一行直接设置本期剩余流量（只改 PORT 和 LEFT_GIB）</summary>

```bash
PORT=40020 LEFT_GIB=85 bash -c 'set -Eeuo pipefail; umask 077; [[ "$(id -u)" == "0" ]] || { echo "请以root运行" >&2; exit 1; }; [[ "${PORT:-}" =~ ^[0-9]{1,5}$ ]] && (( 10#$PORT >= 1 && 10#$PORT <= 65535 )) || { echo "端口无效" >&2; exit 1; }; [[ -n "${LEFT_GIB:-}" ]] || { echo "请填写LEFT_GIB" >&2; exit 1; }; source /usr/local/lib/hy2/common.sh; source /usr/local/lib/hy2/quota-lib.sh; WANT="$(hy2_parse_gib_to_bytes "$LEFT_GIB")" || hy2_die "剩余额度无效"; [[ "$WANT" =~ ^[0-9]+$ ]] && (( WANT > 0 )) || hy2_die "剩余额度必须大于0"; hy2_ensure_runtime_dirs; hy2_acquire_lock_fd 7 "${HY2_LOCK_DIR}/temp.lock" 120 "节点锁繁忙"; export HY2_TEMP_LOCK_HELD=1; hy2_pq_lock; T="$(hy2_temp_meta_by_port "$PORT")"; [[ -n "$T" && -f "$T" ]] || hy2_die "不是受管HY2临时节点"; TAG="$(hy2_meta_get "$T" TAG)"; Q="$(hy2_quota_meta_file "$PORT")"; [[ -f "$Q" ]] || hy2_die "没有配额元数据"; [[ "$(hy2_meta_get "$Q" PORT)" == "$PORT" && "$(hy2_meta_get "$Q" OWNER_KIND)" == "temp" && "$(hy2_meta_get "$Q" OWNER_TAG)" == "$TAG" ]] || hy2_die "配额归属不匹配"; ORIG="$(hy2_meta_get "$Q" ORIGINAL_LIMIT_BYTES)"; EXPECTED="$(hy2_meta_get "$T" PQ_LIMIT_BYTES)"; PENDING="$(hy2_meta_get "$Q" REBUILD_PENDING)"; [[ "$ORIG" =~ ^[0-9]+$ && "$ORIG" == "$EXPECTED" && "$PENDING" == "0" ]] || hy2_die "配额结构异常或待恢复"; (( WANT <= ORIG )) || hy2_die "剩余不能超过原始周期配额"; NEXT="$(hy2_meta_get "$Q" NEXT_RESET_EPOCH)"; INTERVAL="$(hy2_meta_get "$Q" RESET_INTERVAL_SECONDS)"; EXPIRE="$(hy2_meta_get "$Q" EXPIRE_EPOCH)"; DURATION="$(hy2_meta_get "$Q" DURATION_SECONDS)"; CREATED="$(hy2_meta_get "$Q" CREATED_EPOCH)"; LAST="$(hy2_meta_get "$Q" LAST_RESET_EPOCH)"; START="$(hy2_meta_get "$T" CREATE_EPOCH)"; for V in "$NEXT" "$INTERVAL" "$EXPIRE" "$DURATION" "$CREATED" "$LAST" "$START"; do [[ "$V" =~ ^[0-9]+$ ]] || hy2_die "周期元数据无效"; done; NOW="$(date +%s)"; (( INTERVAL == 2592000 && DURATION > INTERVAL && NEXT > NOW + 60 && EXPIRE > NOW && START > 0 && START <= NOW && EXPIRE == START + DURATION )) || hy2_die "没有有效的未来30天周期或节点已到期"; [[ "$(hy2_meta_get "$T" DURATION_SECONDS)" == "$DURATION" && "$(hy2_meta_get "$T" EXPIRE_EPOCH)" == "$EXPIRE" ]] || hy2_die "节点生命周期元数据不匹配"; IFS="|" read -r STATE TOTAL USED LEFT <<< "$(hy2_pq_snapshot_unlocked "$PORT")"; [[ "$STATE" == active || "$STATE" == exhausted ]] && [[ "$TOTAL" == "$ORIG" && "$USED" =~ ^[0-9]+$ && "$LEFT" =~ ^[0-9]+$ ]] || hy2_die "实时nft配额不健康"; BACKUP="$(mktemp -d "/root/hy2-set-left-${PORT}-XXXXXXXX")"; chmod 700 "$BACKUP"; cp -p -- "$Q" "$BACKUP/quota.env"; cp -p -- "$T" "$BACKUP/node.env"; echo "原状态备份: $BACKUP"; NEW_USED=$((ORIG-WANT)); if ! hy2_pq_write_meta "$PORT" "$ORIG" "$NEW_USED" "$WANT" temp "$TAG" "$DURATION" "$EXPIRE" "$NEXT" "$INTERVAL" "$CREATED" "$LAST" "$NOW" 1; then hy2_die "写入失败；保留私有备份，请检查状态"; fi; if ! hy2_pq_rebuild_port "$PORT" "$WANT"; then hy2_die "nft规则重建失败；保留备份和待恢复标志，请先排查，不要盲目重试"; fi; if ! hy2_meta_upsert "$Q" REBUILD_PENDING 0; then hy2_die "恢复标志清理失败；保留备份，请先排查"; fi; echo "已设置端口 $PORT 当前剩余 $LEFT_GIB GiB；原周期总额与下次重置时间不变"; TZ=Asia/Shanghai date -d "@$NEXT" "+下次重置（北京时间）：%F %T"; echo "请执行 pq_audit.sh $PORT 核对；此处已用量是计费值，可能包含人为虚拟用量"'
```

</details>

**执行结果**：原始周期总额仍为 200 GiB，本期计费已用调整为 `200 − 85 = 115 GiB`、本期剩余变为 85 GiB；**下一个正常自动重置周期仍恢复 200 GiB**，下次重置日期、节点过期时间、端口、密码、订阅链接均不修改。期间的新流量继续消耗这 85 GiB。流量统计里的计费 `USED` 可能包含人为设置的虚拟用量，**不等于真实消耗**，真实日流量历史应另外查询 `hy2_traffic`。

**处理步骤与失败边界：** 此命令先获取临时节点锁和配额锁，核验配额与节点归属，检查有效 30 天周期和 nft 实时状态，然后在 `/root/hy2-set-left-端口-随机字符/` 备份原配额及节点元数据（root 私有），更新原计费已用量并重建本端口的 UDP 配额规则。它不会修改其他端口、WG、NAT、SOCKS5 或 portbw，不安装服务。**但是它会真实修改指定用户的计费配额与 nft 规则，可能影响正在传输的数据**；同一周期重复执行会重新赋予指定剩余额度。

若配额元数据写入后 nft 重建失败，脚本会非零退出、保留私有备份和 `REBUILD_PENDING` 标志；现有重建函数尝试将该端口 fail-closed。**此时不能盲目重试，也不能擅自清除待恢复标志**，应先检查 `pq_audit.sh`、`hy2_doctor.sh --strict` 与对应规则，由有经验的操作者定位并恢复。终端显示成功后也要核对：

```bash
pq_audit.sh 40020
hy2_audit.sh
```

**验证状态：** 此一行操作已依据当前 `hy2.sh` 的配额元数据/锁/重建函数进行代码核查，并用隔离模拟数据完成正常调整、耗尽后恢复、超额/无效周期/异常状态拒绝、重建失败保留待恢复标志等检查；**没有在真实 Debian VPS 或真实客户节点上执行，因此尚不能称为真机验收通过。** 建议首次使用前在专用测试节点验证当前余额、随后使用、重启持久化以及下一周期恢复，生产节点应先有可恢复快照。

<a id="portbw"></a>

### 自动限速标准：40→18 Mbps，持续 45 秒触发

在实际需要限速的服务器执行；示例端口为 `40000`。整行复制即可：

```bash
portbw auto set 40000 --up 40 --down 40 --trigger 100 --after 45s --auto-up 18 --auto-down 18 --hold 120s --cooldown 0s
```

<details>
<summary>自动限速参数、恢复规则与关闭自动模式</summary>

上传 / 下载分别触发。100% 指本方向 40 Mbps；85% 只用于采样连续性判断，整段窗口仍需达标。保护至少 120 秒，高负载会续期；恢复后零冷却，再次触发仍需重新满足 45 秒条件。手动 set/up/down 会关闭自动模式。节点删除或到期会清理对应端口的限速记录，失败时保留节点元数据供重试。限速只覆盖本机端口，不覆盖任意 WG/NAT 转发；完整双向限速使用默认 nft+tc 模式。

同一端口的 TCP/UDP、IPv4/IPv6 共用上传额度，并共用另一份下载额度，不是每种协议各分一份。静态限速中 `0` 表示该方向不限速。`--nft-only` 不支持下载限速。

实际吞吐可能受协议开销、丢包和瞬时突发影响，不能要求客户端每一瞬间都精确等于配置值。

自动模式只有 `--cooldown` 可省略，默认 `60s`；零冷却必须明确填 `--cooldown 0s`，其他自动参数均必填。两方向均须满足 `0 < 降速值 < 基础速度`；`--trigger` 的单位为百分比，不是 Mbps。

设置后用 `portbw report` 核对；需要采样进度或内核故障检查时，见[补充查询](#advanced-queries)。

**自动降速完整核对顺序：** 设置前用 `portbw report` 保存原状态，设置后分别用 `portbw report`、`portbw auto status 40000` 和 `portbw audit` 查看端口基础限速、采样进度、异常状态。`portbw auto off 40000` 只取消自动策略、恢复该端口的基础上下行限制；`portbw del 40000` 则删除此端口整份 portbw 策略。两个动作不同，不应混用。端口上 TCP 与 UDP 上行共用一份聚合上限、下行另共用一份，**不是协议之间各分独立带宽**。

若服务日志发生轮转，`journalctl -u portbw-watch.service` 查询不到旧降速事件不等于此前从未发生过；也不能以单次吞吐低于设定 Mbps 断言守护进程故障。SOCKS5 的端口限速另在独立落地机操作其**本机 TCP 端口**，不在 HY2 VPS 替它设置。

```bash
portbw auto off 40000  # 关闭自动模式，恢复本端口的基础上传 / 下载限速
```

</details>

<details>
<summary>静态限速：设置、修改、取消</summary>

**40001：TCP+UDP 合计上传 10 Mbps / 合计下载 20 Mbps：**

```bash
portbw set 40001 10 20  # 40001：TCP+UDP 合计上传 10 Mbps / 合计下载 20 Mbps
```

**上传上限改为 15 Mbps：**

```bash
portbw up 40001 15      # 上传上限改为 15 Mbps
```

**下载上限改为 30 Mbps（直接限速，不是触发阈值）：**

```bash
portbw down 40001 30    # 下载上限改为 30 Mbps（直接限速，不是触发阈值）
```

**仅关闭下载限速；上传额度不变：**

```bash
portbw down 40001 0     # 仅关闭下载限速；上传额度不变
```

**仅取消端口限速，不删除 HY2 节点：**

```bash
portbw del 40001        # 仅取消端口限速，不删除 HY2 节点
```

</details>



**HY2-NAT 真机测速（2026-11-04）：** `portbw set 40020 10 10`、`portbw report`、`portbw audit` 均正常，用户报告 v2rayN 测速通过，最后 `portbw del 40020` 正常取消。**这是旧主机对特定 HY2 链路的记录；通用自动触发与恢复复用同源码 `jieshu` 验收，不把旧主机当作当前 VPS。**

**节点回收：** HY2 临时节点到期或删除时，会调用共享 `portbw del`，只删除该节点端口已保存的策略。发现对应记录但 CLI 缺失或删除失败时，保留节点元数据并报告失败，修复后重试；不清理其他端口、不卸载共享 portbw。WG-NAT 使用 HY2 VPS 上节点入口的端口策略，同数字端口的 TCP + UDP 共用额度；不要把 NAT 出口机的 WG `51820` 当作单个 HY2 节点限速端口。

<details>
<summary>可选 SOCKS5：配额、IP 槽位与主动恢复</summary>

仅在独立 SOCKS5 落地机执行：

```bash
socks5 ip-show 41004
socks5 ip-set 41004 2 60
socks5 ip-del 41004
socks5 pq-set 41004 5 --confirm-reset
socks5 pq-del 41004
socks5 watch
```

`pq-set` 将配额重设为 5 GiB、已用量清零并重设 30 天周期，需要显式 `--confirm-reset`；不是追加余额。`ip-set` 重置已有占位。`watch` 会修复规则或异常服务，不是只读查询。

| 管理动作 | 命令 | 影响范围 |
|---|---|---|
| 查看 IP 占位 | `socks5 ip-show 41004` | 查询，不修改占位 |
| 重设来源上限与占位 | `socks5 ip-set 41004 2 60` | 重置本账号的来源占位，可能影响正在使用的来源 |
| 取消来源上限 | `socks5 ip-del 41004` | 不删除账号 |
| 重设总配额为 5 GiB | `socks5 pq-set 41004 5 --confirm-reset` | **清空已有用量**；不是购买额外 5 GiB |
| 取消总配额 | `socks5 pq-del 41004` | 取消限制，风险应由操作者评估 |
| 主动修复防护/服务 | `socks5 watch` | **可能修改规则或服务状态**，不建议随意在生产落地机运行 |

涉及真实用户账号时，先记录原配额、到期时间、IP 占位和快照；不要把只读查询与会重置用量的命令混在一次批处理里。

SOCKS5 使用同一独立 [portbw](#portbw)，在落地机安装后对**本机**端口设置。原样 SOCKS5 的账号创建、到期、删除不自动增删 portbw 策略；HY2 的节点清理集成不作用于 SOCKS5。路由器映射 `51004 → 41004` 时，限速设置在 `41004`。

</details>

<a id="troubleshooting"></a>
## 四、故障排查

<a id="trouble-guide"></a>

### 从症状出发

| 现象 | 先看什么 | 处理边界 |
|---|---|---|
| HY2 主节点 active 但客户端不通 | `hy2_doctor.sh --strict`、UDP 443、DNS A 记录、客户端 SNI | 确认云安全组/防火墙，勿反复重装 |
| 某临时节点突然连不上 | `hy2_audit.sh` + `pq_audit.sh` | 检查到期、配额耗尽或 IP 槽位占满 |
| NAT 节点无法创建 | `wg_nat_healthcheck.sh` / `wg show wg-nat` | 先检查 WG 握手、路由、NAT Peer |
| WG 断开导致 NAT 节点无法联网 | `ip -4 route show table 100` | 若仍有 `prohibit default` 是预期 fail-close，不可改走 VPS |
| 刚重启时 NAT 节点短暂启动失败 | `journalctl -b -u hy2-temp-对应TAG.service` | WG 首次握手可能延后，观察是否自动重试成功 |
| 首次整机重启配额变成 0 | `systemctl is-active hy2-managed-shutdown-save.service` | 初装启动缺陷已由 [首次关机保存修复](https://github.com/liucong552-art/hy2jieshu/commit/893bb2dc25cc96bd7076849385d79ebefd730952) 修复 |
| doctor 警告缺少 `HYSTERIA_BINARY_SHA256` | `hy2_doctor.sh --strict` | 未配置持续核心校验，不是连接故障 |
| 到期节点端口未释放 | `journalctl -u hy2-gc.service -n 50 --no-pager` | 查 GC timer 和防火墙状态，不要盲目覆盖端口 |
| HY2 节点限速异常或清理报错 | `portbw report`、`portbw audit`、`portbw show 40020` | 删除节点会清对应端口策略；失败会保留元数据，修复限速器后重试节点清理 |

### 常用只读检查

```bash
systemctl is-active hy2.service wg-quick@wg-nat.service
systemctl list-timers --all hy2-gc.timer pq-save.timer hy2-managed-watchdog.timer
journalctl -u hy2.service -n 50 --no-pager
journalctl -u hy2-managed-watchdog.service -n 50 --no-pager
journalctl -u wg-quick@wg-nat.service -n 50 --no-pager
```

`hy2_restore_all.sh` 或启动 watchdog 会修改规则与服务状态，**不是纯查询**；优先收集状态与日志后再进行恢复。

- 主节点和临时节点启动前会检查防护规则
- 配额或 IP 限制丢失时，watchdog 尝试恢复
- 无法恢复时停止对应监听，保持 fail-close
- WG-NAT 故障时，策略路由 `prohibit` 和 OUTPUT REJECT 防止出口泄漏
- 临时节点创建采用事务式清理，失败不会保留半套状态
- Hysteria 核心升级失败会恢复旧二进制与原活跃服务
- 证书续期钩子会验证证书有效期及公私钥匹配
- 已到期节点不会在证书续期时被错误重启
- 配置了 `HYSTERIA_BINARY_SHA256` 时，doctor 会检查当前核心哈希

手动触发全部保护恢复：

```bash
/usr/local/sbin/hy2_restore_all.sh
```

手动触发 watchdog：

```bash
systemctl start hy2-managed-watchdog.service
```

手工 guard 状态存在时，看门狗会先 audit、必要时 restore，再次 audit。缺少工具或仍无法恢复时，主节点与临时节点都停止，元数据保留，避免丢失暂停/黑名单后继续监听。修复工具或持久状态后，先恢复并核查防护，再启动主节点和临时节点恢复任务：

```bash
hy2-guard restore && hy2-guard audit && systemctl start hy2.service
systemctl start hy2-managed-watchdog.service
```

仅因手工 guard 故障被安全停止的主节点需要上述显式启动；不要在防护未恢复时直接绕过检查启动服务。

### 按症状顺序排查：从只读到必要修复

| 故障现象 | 第一步（只读） | 第二步（确认后） | 不应做的事 |
|---|---|---|---|
| 主节点无法连接 | `hy2_doctor.sh --strict`、`journalctl -u hy2.service -n 50 --no-pager` | 检查域名 A、TLS/SNI、UDP/443 与云防火墙 | 把 `ss -ltn` 的 TCP/443 状态当作 HY2 结论 |
| 某个临时节点拒绝新来源 | `hy2_audit.sh`、`pq_audit.sh`、`hy2-guard status` | 分别判断到期、配额、IP 槽位或手工封禁 | 在原因未明时直接清零配额或取消所有黑名单 |
| 自动降速不恢复 | `portbw report`、`portbw audit`、`portbw auto status 40020` | 核对采样窗口、触发及恢复规则 | 清空全局 nft/tc，影响其他业务 |
| NAT 出口不可用 | `wg show wg-nat`、只读预检及错误日志 | 核对握手、Peer、mark 路由与 fail-closed 状态 | 把 NAT 故障节点直接改成 VPS 出口而泄漏 |
| 手工暂停仍生效 | `hy2-guard status`、`hy2-guard audit` | 若已获授权，按[暂停与黑名单章节](#pause-port)处理对应端口 | 直接删除整个 `nftables` ruleset |
| SOCKS5 账号连接异常 | **在落地机**查 `socks5 list`、`socks5 status` | 再按现有账号与访问审计记录定位 | 在 HY2 入口机运行 SOCKS5 管理/重装命令 |

只读检查完成后，才考虑确有必要的服务恢复。服务器有真实用户时，不应把“功能已在 CI 通过”当作允许立即重启或重装的理由。恢复后需核查实际客户端连接，不以 `systemctl active` 单独认定公网业务正常。

<a id="service-management"></a>

<details>
<summary>服务管理、重启恢复与证书检查</summary>

主节点与每个临时节点各自为一个 systemd 服务；管理器安装后启用恢复、配额保存、到期回收和看门狗。每日流量与手工黑名单安装后各有独立服务。

| 服务 / 定时器 | 作用 |
|---|---|
| `hy2.service` | 主节点；`systemctl restart hy2.service` 只重启主节点 |
| `hy2-temp-节点名称.service` | 对应临时节点；完整名称以 `hy2_audit.sh` 为准 |
| `hy2-managed-restore.service` | 开机恢复受管理配额、IP 限制和节点保护 |
| `hy2-managed-watchdog.timer` | 定期检查并恢复异常临时节点，失败保持阻断 |
| `hy2-gc.timer` | 回收自然到期临时节点 |
| `pq-save.timer` / `pq-reset.timer` | 定期保存已用量 / 检查到期的 30 天周期 |
| `hy2-managed-shutdown-save.service` | 正常关机前保存受管理配额 |

```bash
systemctl list-timers --all hy2-managed-watchdog.timer hy2-gc.timer pq-save.timer pq-reset.timer
systemctl status hy2-managed-restore.service hy2-managed-shutdown-save.service --no-pager
```

临时停止服务后，看门狗可能重新启动它；需要暂停用户连接时用 `hy2-guard pause 端口`，永久撤销用[删除节点](#node-manage)。正常 `reboot` 会经过保存流程；异常断电可能丢失最后一次保存后的流量，不将这两类情况混为一谈。

证书通过 acme.sh 定时续期及 HY2 reload hook 验证和应用；先检查证书与日志，避免为排障反复强制签发而触发 CA 限额：

```bash
CERT=$(awk -F= '$1=="TLS_CERT"{print substr($0,index($0,"=")+1); exit}' /var/lib/hy2/main/main.env)
openssl x509 -in "$CERT" -noout -subject -issuer -dates
journalctl -u hy2.service -n 50 --no-pager
```

证书路径由 `/var/lib/hy2/main/main.env` 的 `TLS_CERT` 读取，通常为 `/etc/hysteria/certs/域名/fullchain.pem`。续期测试、升级回滚和故障注入的实际验收范围见[验收记录](#acceptance)。

</details>

<a id="remove"></a>
## 五、暂停、封禁与删除

<a id="port-block"></a>

**已实现**：`hy2-guard.py` 提供真正可持久化的整端口暂停 / 恢复与来源 IP/CIDR 黑名单，规则在独立 `inet hy2_manual_guard` 表中。不会修改 `hy2_pq`、`hy2_iplimit`、WireGuard、Hysteria 服务或其他端口；修改时仅校验端口属于已登记的 HY2 主节点或临时节点；规则按同一数字端口同时作用于 TCP 和 UDP，必须避免将 HY2 端口复用为 SSH 等管理端口，否则可能同时阻断管理连接。初次使用先完成下面的安装。

### 初次安装（HY2 VPS 执行）

```bash
curl -fL --retry 3 https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/hy2-guard.py -o /root/hy2-guard.py
python3 -m py_compile /root/hy2-guard.py
python3 /root/hy2-guard.py install
hy2-guard audit
```

安装生成 `/usr/local/sbin/hy2-guard` 和 `hy2-manual-guard.service`；重启后由 systemd 恢复持久规则。依赖 `nftables`、`python3`、`systemd`。只对 `inet hy2_manual_guard` 表进行原子事务，**不会执行 `nft flush ruleset`**。对于真正的恢复和安全边界，仍需在目标 VPS 上用单独测试端口做一次真机验证。

<a id="pause-port"></a>

<details>
<summary>端口暂停：封禁、解封、状态查询</summary>

以下操作不会删除节点、重置配额或停止 HY2 服务；暂停时外部 IPv4/IPv6 的 TCP/UDP 入站会被丢弃。示例 UDP/40020，先确认这是需要管理的 HY2 节点：

```bash
hy2_audit.sh
hy2-guard pause 40020
hy2-guard status
hy2-guard audit

# 恢复此端口的外部连接
hy2-guard resume 40020
hy2-guard audit
```

恢复后如还有独立配额、IP 限制、黑名单或 portbw 限速，它们继续生效。守护进程不会自行撤销手工暂停。

</details>

<a id="source-blacklist"></a>

<details>
<summary>来源 IP / CIDR 黑名单：单 IP、网段、批量逐条管理</summary>

支持 IPv4 和 IPv6，输入 CIDR 时必须填写规范网络地址（例如 `203.0.113.0/24`；不是 `203.0.113.123/24`）。以下都只影响指定 HY2 端口：

```bash
# 单独拉黑一个 IPv4 来源
hy2-guard ban 40020 198.51.100.8

# 拉黑整个来源网段
hy2-guard ban 40020 203.0.113.0/24
hy2-guard ban 40020 2001:db8::/32

# 解除其中一个网段，不影响其他规则
hy2-guard unban 40020 203.0.113.0/24

# 清空仅此端口的黑名单，不会取消整端口暂停
hy2-guard clear 40020
```

**区别**：`IP_LIMIT=1` 是最多同时允许一个活跃来源 IP；`hy2-guard ban` 则直接封禁具体来源地址或网段，它们各自独立，互不替代。手工黑名单支持持久化，暂停与封禁均覆盖同数字端口的 TCP + UDP。新版节点清理会调用 `hy2-guard forget` 删除该端口的暂停与黑名单，避免端口复用继承旧规则。

#### 多个来源 IP：逐条执行与逐条撤销

先确认端口属于目标 HY2 节点，且**不是 SSH 或其他管理服务使用的端口**。以下仅为示例测试地址，须替换为你明确要处理的来源 IP：

```bash
# 对端口 40020 按来源逐条封禁；某条失败立即停止
for ip in 198.51.100.8 198.51.100.9; do
  hy2-guard ban 40020 "$ip" || break
done
hy2-guard status
hy2-guard audit

# 只解除指定两条记录；不清除其他来源封禁
for ip in 198.51.100.8 198.51.100.9; do
  hy2-guard unban 40020 "$ip" || break
done
hy2-guard audit
```

`clear 40020` 会清除该端口全部来源黑名单，而 `resume 40020` 只撤销端口暂停；两者不是同一个动作。规则同时覆盖**该数字端口的 TCP 与 UDP**，不会因为 HY2 的业务承载协议为 UDP 就自动放过 TCP。

<a id="blacklist-report"></a>

### 查询所有受管理暂停与黑名单

```bash
hy2-guard status
hy2-guard audit
systemctl is-enabled hy2-manual-guard.service
systemctl is-active hy2-manual-guard.service
```

若需手动撤销某端口的暂停及全部来源黑名单，可在核对归属后执行 `hy2-guard forget 40020`；这不会删除 HY2 节点或修改其配额。

如果因外部清空表导致 `audit` 失败，在确认没有其他管理器冲突后，可运行 `hy2-guard restore` 恢复独立表。恢复只使用本模块的状态文件，不读取任意 shell 配置。

</details>

<a id="node-manage"></a>

<details>

<summary>删除指定 HY2 临时节点 / 清空全部临时节点</summary>

删除临时节点会使对应链接失效，清理其配额/IP 规则、本端口的手工暂停/黑名单及已保存的 portbw 策略；不会删除 HY2 主节点、WireGuard 或其他端口策略。限速 CLI 缺失或删除失败时会报错并保留节点元数据，修复后重试。清理前先运行 `hy2_audit.sh` 确认完整 TAG。

#### 强制删除一个临时节点

先运行 `hy2_audit.sh` 找到完整 TAG，然后执行：

```bash
FORCE=1 hy2_cleanup_one.sh hy2-temp-节点名称
```

普通临时节点与 WG-NAT 临时节点使用同一清理命令。

#### 清空全部临时节点

```bash
hy2_clear_all.sh
```

批量清理会尝试各个受管临时节点，任一节点未清理成功时返回非零；不能把有残留的批次当作清空成功。

</details>

<details>
<summary>删除可选 SOCKS5 账号</summary>

在独立落地机按本机监听端口删除；不会删除 HY2 节点。需要撤销该端口的独立限速时再手动删除对应 portbw 策略：

```bash
socks5 del 41004
```

HY2 的 `hy2_cleanup_one.sh`、`hy2_clear_all.sh` 及 `hy2-uninstall.sh` 不负责 SOCKS5 账号或模块；不要用 HY2 管理命令代替 SOCKS5 命令。

</details>

<a id="uninstall"></a>

<details>
<summary>卸载 HY2：先预览，按需保留或删除数据</summary>

在 HY2 VPS 执行。先下载并查看帮助、预览操作范围：

```bash
curl -fsSL --retry 3 https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/hy2-uninstall.sh -o /root/hy2-uninstall.sh
chmod 700 /root/hy2-uninstall.sh
bash -n /root/hy2-uninstall.sh && bash /root/hy2-uninstall.sh
```

默认只预览。确认备份已保存后，下面两种方式选择一种：

```bash
# 停止并移除 HY2 运行服务及大部分工具，保留数据、证书和 guard 恢复工具
bash /root/hy2-uninstall.sh --yes
```

```bash
# 同时删除 HY2 节点、配额、统计、配置及证书；并移除 Hysteria 核心
bash /root/hy2-uninstall.sh --yes --purge --remove-core
```

卸载会使 HY2 链接停止工作。WireGuard、NAT Peer、portbw 程序、acme.sh 账户与 SSH 配置分别管理，不随 HY2 卸载删除；保留数据卸载时也保留对应端口限速，`--purge` 会清理 HY2 主节点及临时节点元数据所列端口的 portbw 策略，其他端口保留。脚本对共用名称的配额服务和命令进行 HY2 归属检查，拒绝删除其他应用的组件。

保留数据卸载将临时 unit 备份到 root 私有的 `/var/lib/hy2/uninstalled-units/`，备份文件权限为 600；同时保留 `hy2-guard` 命令、停止/禁用的 guard unit 和 `/usr/local/sbin/hy2_nat_preflight.sh`，作为普通 / NAT 节点恢复工具，专用 nft 表会移除。重新安装管理器时，在 GC 之前恢复合法未到期 unit，先恢复 guard 规则与服务，确认防护后才启动保留节点。普通与 NAT 两节点的完整保留数据卸载/重装已在[本轮报告](tests/REAL_MACHINE_ACCEPTANCE_2026-11-15.md)通过外部客户端复测；前两次失败及修复过程仍保留。

`--purge` 删除的数据无法由 GitHub 恢复；`/root/.acme.sh` 中的账户及 ACME 证书副本仍保留，不能将此命令当作所有密钥的彻底销毁。保留数据卸载后重新安装也必须检查旧节点有效期和防护，不能将它当作空白机直接运行首次安装前置检查。

</details>

<a id="install"></a>

## 六、安装与更新

按组件展开。**WG-NAT 保留完整两端部署顺序，其他组件也保留完整安装和更新步骤。**

<details>
<summary>环境要求与各脚本运行位置</summary>

### 使用前准备

- HY2 / WG-NAT：Debian 11+ 或 Ubuntu 20.04+，使用 `root`，系统由 systemd 管理。
- 一个 A 记录指向**新 HY2 VPS** 的公网 IPv4；创建 IPv6 临时节点时，再准备相应 AAAA 记录。
- TCP `80` 可从公网访问以完成首次 TLS 证书签发；放行主节点 **UDP `443`** 和需要的临时节点 UDP `40000–50050`。
- WG-NAT 使用的 UDP 端口默认是 `51820`，需按两端实际防火墙与网络条件放行。
- Cloudflare 等 DNS 服务必须为 **DNS only**，不能让 HY2 的 UDP 连接走普通网页代理。
- 本文是 **Bash 命令**；域名、邮箱、公钥和 Peer 名称必须替换为真实值。

> **部署位置固定：** `hy2.sh`、`vpswg.sh`、`natjichang.sh` 在**新 HY2 VPS** 上运行。`nat.sh` 仅在 **NAT 出口机** 使用。你已经验收的 `jieshu` NAT 直接共用，不下载、不覆盖、不重新安装 HY2 版 NAT。不同项目分别部署在不同 VPS，`helan` 测试机的数据不需要迁移。

### 先确认运行位置

| 组件 / 文件 | 在哪台机器运行 | 用途 |
|---|---|---|
| `hy2.sh` | 新 HY2 VPS | 安装主节点、普通临时节点和管理组件 |
| `vpswg.sh` | 新 HY2 VPS | 配置 WG-NAT 的 VPS 端 |
| `natjichang.sh` | 新 HY2 VPS | 安装 WG-NAT 临时节点工具 |
| `nat.sh` | 已有 jieshu NAT 出口机 | 继续使用原管理器；只有新 VPS 缺少 Peer 时才正常新增 |
| `traffic.py` | 新 HY2 VPS | 可选：UDP 每日流量统计 |
| `portbw-install.sh`、`portbw.py` | 需要限速的 VPS | 可选：直接复用 jieshu 已验收的通用源码 |
| `hy2-guard.py`、`hy2-abuse.py` | 新 HY2 VPS | 可选：防火墙管理、异常审计 |
| `socks5-install.sh`、`socks5.py`、`socks5-traffic.py`、`socks5-audit.py` | 独立 SOCKS5 落地机 | 手动选择安装：账号、配额、流量及访问审计 |

`tests/` 和 `.github/workflows/` 是项目的测试与 CI，不需要复制到业务服务器。

**三台机器的职责，不要混淆：**

| 部署角色 | 实际安装的协议或工具 | 不应在这台机盲目执行 |
|---|---|---|
| HY2 入口 VPS | Hysteria2、HY2 节点/配额/IP 管理、可选 guard/abuse/portbw、必要时 VPS 端 WG | 不自动安装独立 SOCKS5、不初始化生产 NAT 出口 |
| WG/NAT 出口机 | 原有 `jieshu/nat.sh` 和 WireGuard Peer | 不覆盖已经验收的生产版 NAT 管理器；不为更新 HY2 重启共享 WG |
| SOCKS5 独立落地机 | 原样复用的 SOCKS5 安装器、账号、流量、访问审计；限速另行自选 portbw | 不运行 HY2 主安装器，SOCKS5 也不意味着 HY2 自动经 SOCKS5 转发 |

> README 中的安装、重装、删除、`watch`、`restore`、`probe-*`、`systemctl restart` 等命令均为**操作示例**，不是文档校验过程中应自动执行的步骤。共享生产系统先做快照并安排维护窗口。

需要单独查看系统准备和新 Peer 接入细节时，可参考[全新 VPS 部署手册](docs/FRESH_VPS_DEPLOY.md)；**下面 6.1、6.2 已经包含可直接执行的完整命令，不必跳转后才能安装。**

</details>

<a id="hy2-install"></a>

<details>
<summary>6.1 HY2 主节点：安装 → 配置 → 创建主节点 → 检查</summary>

### 1. 安装

在**全新 HY2 VPS** 执行：

```bash
apt-get update && apt-get install -y curl ca-certificates nano iproute2
```

依赖安装成功后，下载并安装管理工具（修改系统）：

```bash
curl -fsSL --retry 3 'https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/hy2.sh' -o /root/hy2.sh && chmod 700 /root/hy2.sh && bash -n /root/hy2.sh && bash /root/hy2.sh
```

本步骤生成 `/etc/default/hy2-main`、`/root/onekey_hy2_main_tls.sh`、临时节点管理器、配额和 IP 限制、看门狗、恢复任务以及对应 systemd 单元。**安装管理器本身还不会自动创建可连接的 HY2 主节点。**

### 2. 修改配置

在 **HY2 VPS** 执行：

```bash
nano /etc/default/hy2-main
```

下面是**配置文件内容示例**，写进编辑器，不是在终端执行的命令：

```ini
HY_DOMAIN=hy2.example.com
HY_IPV6_DOMAIN=
HY_LISTEN=0.0.0.0:443
ACME_EMAIL=admin@example.com
MASQ_URL=https://www.apple.com/
NODE_NAME=HY2-MAIN
TEMP_PORT_START=40000
TEMP_PORT_END=50050
ENABLE_SALAMANDER=0
HYSTERIA_VERSION=latest
HYSTERIA_UPDATE_POLICY=install-only
```

在 nano 中按 `Ctrl+O`、回车保存，再按 `Ctrl+X` 退出。

通常只需要修改：

- `HY_DOMAIN`：必须有 A 记录指向**当前新 VPS**，不能沿用 `helan` 的域名或旧连接参数。
- `ACME_EMAIL`：填写用于 ZeroSSL/ACME 注册及证书通知的有效邮箱；证书签发前必须确保 TCP/80 可达。
- `HY_IPV6_DOMAIN`：只有准备创建 IPv6 临时节点、且已经配置正确 AAAA 记录时才填写。
- `NODE_NAME`、`TEMP_PORT_START`、`TEMP_PORT_END`：按需调整。主节点固定使用 IPv4 UDP `443`。

`install-only` 意味着后续重复执行主节点部署不会擅自把现有 Hysteria 核心升级到新版。此项目使用受信任的正式 TLS 证书，不以自签证书或客户端跳过证书验证作为正常安装步骤。

### 3. 创建或更新主节点

第一次签发正式 TLS 证书并创建 HY2 主节点，或修改上述配置后重新应用时执行：

```bash
bash /root/onekey_hy2_main_tls.sh
```

**这一步才会实际部署主节点。** 以后日常重新应用主节点，默认按配置的 `install-only` 策略复用已安装的 Hysteria 核心；切换域名之前应先完成新 DNS 和证书条件。

部署成功后查看主节点链接：

```bash
cat /root/hy2_main_url.txt
```

Base64 主节点订阅（需要时再查看）：

```bash
cat /root/hy2_main_subscription_base64.txt
```

链接包含密码，只在自己的客户端导入，不要发到 GitHub、公开日志或聊天截图。**新 VPS 生成新凭据，不复制 `helan` 测试机的链接或密钥。**

<details>
<summary>高级选择：显式升级 Hysteria 核心（日常不必执行）</summary>

升级前先建立 VPS 快照并确认正式维护窗口；不要用升级操作代替普通安装。将 `vX.Y.Z` 换成要升级的实际版本：

```bash
HYSTERIA_FORCE_UPDATE=1 HYSTERIA_VERSION=vX.Y.Z bash /root/onekey_hy2_main_tls.sh
```

确实需要官方当前稳定版时也可以指定 `HYSTERIA_VERSION=latest`。升级程序会预检候选核心、备份旧核心，在出错时尝试回滚；只有文件、核心和原活跃服务恢复验证成功才报告完成。回滚失败会返回非零、记录失败步骤并保留私有备份路径，需按日志处理；生产环境优先使用经过验收的确定版本和有效的 `HYSTERIA_BINARY_SHA256`。

</details>

### 4. 怎样确认安装成功

在 **HY2 VPS** 执行：

```bash
systemctl is-active hy2.service
ss -lun '( sport = :443 )'
hy2_doctor.sh --strict
```

正常情况：`hy2.service` 显示 `active`、`ss` 能看到 **UDP/443** 监听，Doctor 不报告关键错误。HY2 使用 UDP，**不是** `jieshu` VLESS 使用的 TCP/443；不能照抄 `ss -ltn` 检查。

然后将 `/root/hy2_main_url.txt` 中的完整 `hy2://` 链接导入 v2rayN 等兼容客户端，从**另一台设备**实际联网验证。**本机显示 active 和端口监听，不等于外部客户端一定可用。**

连接失败先查看[故障排查](#trouble-guide)，检查 A 记录、TCP/80 证书签发情况、UDP/443 防火墙和客户端配置，不要随意清空 nftables 或重新生成旧节点凭据。

</details>

<a id="wg-nat"></a>

<details>
<summary>6.2 WG-NAT：完整五步部署、NAT 管理与 Peer 探测</summary>

WG-NAT 让 HY2 VPS 上指定的临时节点通过另一台机器的公网 IPv4 出口访问互联网。**已验收的 `jieshu` NAT 直接复用**；下面的步骤 1 只用于尚未部署 NAT 的新机。新 HY2 VPS 需有自己的 WireGuard Peer，不能复制 `helan` 测试机的私钥。

### 1. 初始化 NAT 出口机（只有全新、尚无 NAT 的机器才执行）

**你的现有 NAT 机已经安装并通过 `jieshu/nat.sh` 验收：跳过此步，不执行 HY2 `nat.sh init`，不覆盖原 `/root/nat.sh`。** 共享 NAT 上执行 `init/add/del` 可能重启整个 WG 接口，影响其他 VPS。

如果未来另建一台**完全空白** NAT 出口机，才在那台 NAT 机执行下面的**新安装**示例：

```bash
apt-get update && apt-get install -y curl ca-certificates
curl -fsSL --retry 3 'https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/nat.sh' -o /root/nat.sh && chmod 700 /root/nat.sh && bash -n /root/nat.sh && bash /root/nat.sh init
```

无法自动识别 WAN 网卡时，只在全新 NAT 机按实际名称指定 `WAN_IF=实际网卡`；不要从新机部署步骤反向修改现有 `jieshu` NAT。

### 2. 配置 HY2 VPS

在**新 HY2 VPS** 执行（下载并部署 VPS 端 WireGuard）：

```bash
curl -fsSL --retry 3 'https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/vpswg.sh' -o /root/vpswg.sh && chmod 700 /root/vpswg.sh && bash -n /root/vpswg.sh && bash /root/vpswg.sh
```

脚本会生成**新 VPS 专属**的 WireGuard 公钥。以后需要查询时，在该 HY2 VPS 执行：

```bash
cat /etc/wireguard/wg-nat.pub
```

### 3. 在已有 jieshu NAT 机添加新 VPS

先在**原 NAT 出口机**查已有 Peer：

```bash
bash /root/nat.sh list
```

如果这台新 HY2 VPS 已有**公钥、地址都正确**的独立 Peer，不需要重复 `add`。如果还没有，在安排好共享 WG 维护窗口后，继续使用 **jieshu 原有 `nat.sh`** 添加新 Peer（Peer 名不可与其他 VPS 重复）：

```bash
bash /root/nat.sh add hy2 hy2.example.com '这里替换成新HY2_VPS的WireGuard公钥'
```

三个参数分别是：

- `hy2`：这台新 VPS 在 NAT 机的**唯一 Peer 名称**，例如 `hy2-01` 或 `vps1`；切勿覆盖已有别的 VPS。
- `hy2.example.com`：**新 HY2 VPS** 的公网 IPv4 域名或地址。
- 第三个参数：在**新 HY2 VPS** 执行 `cat /etc/wireguard/wg-nat.pub` 得到的公钥，**不是** `helan` 的旧公钥。

NAT 机会分配 WG 地址并输出 VPS 的完整回填命令。**`nat.sh add` 可能重启共享 WG，导致其他 Peer 短暂断线；不能当成无影响操作。** 现有探测规则、timer 和防火墙仍由 `jieshu` 管理，不部署第二套 HY2 NAT 管理器。

### 4. 回到 HY2 VPS 执行回填命令

在**新 HY2 VPS** 原样执行 NAT 机刚刚打印的 `wg_nat_set_peer.sh` 回填命令，**不照抄测试机的公钥、隧道地址或示例凭据**。如忘记 NAT 公钥，可只在 NAT 出口机查询：

```bash
cat /etc/wireguard/wg-exit.pub
```

新 HY2 VPS 回填后检查 WG 出口：

```bash
/usr/local/sbin/wg_nat_healthcheck.sh
```

**注意：这条健康检查是主动修复型检查**：它可能调整本机 rp_filter、并调用 WG guard 修复策略路由/防火墙；**不是只读操作**。仅需不修改系统的状态核验，可运行 `bash /root/hy2_fresh_preflight.sh wg`（需先按[全新 VPS 手册](docs/FRESH_VPS_DEPLOY.md)下载），它只查询最近握手和 mark 路由，不会实际发起 NAT 出口 IP 探测。

成功时应出现类似 `OK EXIT_IP=...`。若失败，先确认新 Peer 公钥、AllowedIPs、UDP/51820 和握手情况，不要在已有 NAT 机上重复执行 `init`。

### 5. 安装 WG-NAT 临时节点工具

在**新 HY2 VPS** 执行（只更新 VPS 端模块，不动 NAT 机）：

```bash
curl -fsSL --retry 3 'https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/natjichang.sh' -o /root/natjichang.sh && chmod 700 /root/natjichang.sh && bash -n /root/natjichang.sh && bash /root/natjichang.sh
```

检查新 VPS 的 WG-NAT 准备情况：

```bash
bash /root/natjichang.sh check
```

配置完成后，需要 NAT 出口的 HY2 临时节点使用 `hy2_mktemp_nat.sh`，普通 HY2 临时节点仍使用 `hy2_mktemp.sh`。

### NAT 出口机日常管理

以下命令**仅在现有 jieshu NAT 出口机**执行，且使用它原有的 `/root/nat.sh`：

#### 查询已有 Peer 与运行状态

```bash
bash /root/nat.sh list
bash /root/nat.sh status
```

#### 更新或移除某台 VPS

只有确实需要变更 Peer 时才执行 `add` 或 `del`；它们可能重启整个共享 WG。先用 `list` 找到真实 Peer 名，不要把例子中的 `hy2` 当作现有节点：

```bash
# 更新已存在的同名 Peer（仅在维护窗口）
bash /root/nat.sh add hy2 hy2.example.com '新的VPS的WireGuard公钥'
# 删除某个指定 Peer（危险：此 Peer 会断线）
bash /root/nat.sh del hy2
```

### 单 Peer 探测（可选，直接复用 jieshu）

**这部分已经在 `jieshu` NAT 项目验收过，不必为 HY2 再安装探测器、切换探测管理器或重复测试。** 必须查看某个 Peer 的状态时，仍在 NAT 机使用原版命令：

```bash
bash /root/nat.sh probe-once hy2
bash /root/nat.sh probe-status hy2
```

确实需要控制已有 Peer 的定时器时，再使用 `probe-enable` / `probe-disable`；**不要为了 HY2 验收去启停已经工作的探测定时器**。`WG_PROBE_SENT` 仅表示探测包已尝试发送，不是远端已成功重新握手的证明。

**可选探测的操作边界（仅供确认需要时使用）：**

| 命令 | 作用 | 生产共享 NAT 注意事项 |
|---|---|---|
| `bash /root/nat.sh probe-status hy2` | 查询指定 Peer 探测状态 | 优先使用，避免改变已有 timer |
| `bash /root/nat.sh probe-once hy2` | 主动尝试发送一次探测 | 不是只读；是否成功应再看握手和真实出口 |
| `bash /root/nat.sh probe-enable hy2` | 为指定 Peer 启用探测 | 可能更改定时器；仅在明确授权和维护窗口执行 |
| `bash /root/nat.sh probe-disable hy2` | 为指定 Peer 禁用探测 | 会改变已有监控行为；不为了 HY2 对标随意执行 |

运行 `list` / `status` 前先确认登录的是**落地 NAT 出口机**，不是新 HY2 VPS。共享出口机已有真实用户时，不执行 `init`、无目的的 `add` / `del`、WG 重启或“为了演示命令”的探测操作；新 VPS 的独立 Peer 已存在就直接复用。

</details>

<a id="daily-install"></a>

<details>
<summary>6.3 HY2 每日流量：独立安装 / 更新</summary>

在已经安装 HY2 管理器的 **HY2 VPS** 上，以 `root` 执行。独立统计组件支持主节点、普通临时节点及 WG-NAT 临时节点；按 UDP 端口统计，无需重新安装主节点或重启 Hysteria。

### 安装 / 更新

在 HY2 VPS 下载并安装统计组件（首次安装和后续更新使用同一命令）：

```bash
curl -fsSL --retry 3 'https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/traffic.py' -o /root/hy2_traffic.py && python3 -m py_compile /root/hy2_traffic.py && python3 /root/hy2_traffic.py --install
```

安装器会管理 `hy2-traffic.timer`、`hy2-traffic.service` 及 `hy2-traffic-shutdown.service`。旧的历史数据应当保留；不需要执行 `hy2.sh` 重装，也不会更改 `pq-save.timer`。

### 检查统计与历史

```bash
systemctl is-active hy2-traffic.timer hy2-traffic-shutdown.service
systemctl list-timers --all hy2-traffic.timer
hy2_traffic
hy2_traffic main
hy2_traffic 40020 --json
```

`40020` 是示例端口，请先从 `hy2_audit.sh` 查到真实端口。`hy2-traffic.service` 为定时 oneshot，执行结束后显示 inactive 属正常情况；关机保存服务使用 `RemainAfterExit=yes`。具体日流量与配额可能采样时间不同，先核对采样时间，不要直接当成实时限速数字。

</details>

<a id="portbw-install"></a>

<details>
<summary>6.4 portbw：完整首次安装、受管理版本升级与旧版本迁移</summary>

### 安装 / 更新 portbw（需要同时下载两个文件）

**运行位置：需要限速的服务器。首次安装和升级分开操作。**

1. 仅限没有旧 portbw 的新安装环境，先安装依赖（修改系统）：

```bash
apt-get update && apt-get install -y curl ca-certificates python3 iproute2 nftables util-linux coreutils procps
```

依赖安装成功后，下载两个配套文件；以下命令仅下载，不安装、不创建限速策略：

```bash
curl -fsSL 'https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/portbw-install.sh' -o /root/portbw-install.sh && \
curl -fsSL 'https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/portbw.py' -o /root/portbw.py
```

两次下载均成功后再继续。已有 portbw 的主机应看下面的升级说明，不要执行新安装流程。

2. 预检环境和配套源码（不安装 portbw）：

```bash
bash /root/portbw-install.sh check
```

**只在出现 `CHECK PASS` 后继续。** 若提示已有安装，不要删旧文件来强行通过，改看下面的升级 / 迁移说明。

3. 执行实际安装（修改系统）：

```bash
bash /root/portbw-install.sh install
```

应出现 `INSTALL PASS` 和 `VERIFY PASS`；仅下载文件、语法检查或运行 `check` 都不会完成安装。首次安装不会自动创建端口限速策略。

4. 核对安装结果：

```bash
command -v portbw
bash /root/portbw-install.sh verify
systemctl is-active portbw-watch.service
portbw report
portbw audit
```

命令路径应为 `/usr/local/sbin/portbw`，Watchdog 通常为 `active`；尚未设置端口时列表为空属于正常情况。核对通过后，选择后面的静态设置或自动设置。

如预检要求指定物理网卡，先用 `ip -4 route get 1.1.1.1` 查看，再在 `check` 和 `install` 后分别加 `--iface eth0`，把 `eth0` 换成实际物理网卡名；不要根据示例猜网卡。

<details>
<summary>已有受管理版本：升级方法</summary>

**升级已由本系列通用安装器管理的已知 v1/v2/候选版：** 先按上方两条下载命令重新下载同一版安装器和源码，先记录当前的 `portbw report` 与 `portbw audit`，保存可恢复的 VPS 快照，再在维护窗口执行（不要重新执行首次安装 `install`）：

下面三步用 `&&` 串联，前一步失败时不会继续下一步；预检失败时先处理原因，不能跳过：

```bash
bash /root/portbw-install.sh preflight-upgrade && \
bash /root/portbw-install.sh upgrade && \
bash /root/portbw-install.sh verify
```

全部成功后核对：

```bash
portbw report
portbw audit
```

首次安装的 `check` 要求干净环境，已有受管理安装要用 **`preflight-upgrade`**。升级工具只接受有 `/var/lib/portbw-resident-release/current.env` 管理记录，且已安装源码 SHA 与记录一致的受支持旧版；未知来源的旧版即使已有端口配置也**不允许直接覆盖或伪造管理记录**。安装器会持久保存备份，但不能取代 VPS 快照。不要执行 `nft flush ruleset`、`tc qdisc del ... root`，不要停止其他业务的 nft/tc 系统规则。

</details>

<details>
<summary>其他旧仓库 / 无管理记录版本：迁移说明</summary>

**其他旧仓库/无管理记录版本的迁移（不能直接 `install`/`upgrade`）：** 特别是 `zuizhongheji` 等独立旧版及使用旧 tc flower 槽位的机器，先记录每个端口的**基础上/下行、降速上/下行、触发百分比、持续秒数、滚动保护、冷却**，执行 `portbw report` 与 `portbw audit` 并制作 VPS 快照。只可在维护窗口按照确切旧版校验过的迁移工具或逐端口安全删除方法移除旧限速，再安装此通用版并重新添加规则；在删除到重建期间可能暂时失去限速保护。不要把普通安装器用于未知来源旧版本，更不要手动清空整个 nftables ruleset、网卡 root qdisc 或其他业务规则。

</details>

</details>



<a id="socks5"></a>

<details>

<summary>6.5 SOCKS5：独立可选落地、首次安装、更新与每日流量</summary>

四个模块原样复制自 `jieshu` 的 `89c5508`，仅作为**独立落地机上手动选择安装**的可选功能。`hy2.sh` / `nat.sh` / `vpswg.sh` / `natjichang.sh` 不自动安装 SOCKS5，也不让 HY2 流量自动经过 SOCKS5。SOCKS5 仅支持 TCP CONNECT，不支持 UDP ASSOCIATE。

**验收复用：** 直接沿用 [jieshu README 的 SOCKS5 安装说明](https://github.com/liucong552-art/jieshu/blob/89c5508/README.md#socks5)及[历史审计验收记录](https://github.com/liucong552-art/jieshu/blob/89c5508/tests/SOCKS5_AUDIT_REAL_MACHINE_ACCEPTANCE.md)，不新增本轮 HY2 VPS 实测结论、不重复部署或功能测试。上游记有 Debian 12 真机及 Debian 13 暂存检查，也保留干净安装/升级等未覆盖边界；不能扩大为所有系统均通过。

### 1. 四文件同目录下载

以下在**独立 SOCKS5 落地机**以 root 执行；需要安装时才手动运行。先准备下载工具：

```bash
apt-get update && apt-get install -y curl ca-certificates
```

四个文件保持配套，下载失败不继续：

```bash
install -d -m 700 /root/socks5-release && \
curl -fsSL --retry 3 https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/socks5-install.sh -o /root/socks5-release/socks5-install.sh && \
curl -fsSL --retry 3 https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/socks5.py -o /root/socks5-release/socks5.py && \
curl -fsSL --retry 3 https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/socks5-traffic.py -o /root/socks5-release/socks5-traffic.py && \
curl -fsSL --retry 3 https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/socks5-audit.py -o /root/socks5-release/socks5-audit.py
```

### 2. 首次安装 / 已安装版本更新

首次安装：

```bash
bash -n /root/socks5-release/socks5-install.sh && AUTO_DEPS=1 bash /root/socks5-release/socks5-install.sh install
```

原安装器优先读取自身目录的三个模块，并在安装前执行内置 SHA256 校验；必须看到 `[socks5] SHA256 校验通过`，不匹配就停止核对四文件，不能跳过校验。由于安装器也保持原样，若同目录文件不全，它的远程 fallback **仍指向 `jieshu/main`**（或原允许的审计分支），没有改成 HY2；上面的四文件流程使用本仓库配套本地模块。

家宽路由器后的主机可在 `install` 后加 `--host proxy.example.com` 指定真实公网入口；必要时加 `--wan-if 实际网卡`。账号的公网/本机端口映射按[新建 SOCKS5 账号](#socks5-create)设置。

已有账号的主机先保存可恢复快照，按上面下载流程更新四文件，再执行 `update`；不要对已有安装套用首次安装命令：

```bash
bash -n /root/socks5-release/socks5-install.sh && AUTO_DEPS=1 bash /root/socks5-release/socks5-install.sh update
```

更新不会主动清空账号，但迁移访问日志配置可能短暂重启实例；更新后核对账号、配额和实际连接。原安装器没有通用卸载/降级子命令，失败回退使用已验证的整机快照，不编造 `socks5 uninstall`。

**已有生产落地机安全升级核对顺序：** 先保存服务商快照及原账号列表、用量与本机端口，再核对四文件的 SHA/本地校验状态；只有在确实需要升级、获得授权并预留维护窗口时才执行 `update`。更新期间可能短暂重启实例，事后需核对原账号、配额、IP 占位、日志及真实连接。若保持原样且没有升级需求，**什么都不运行**。

SOCKS5 的访问审计、`socks5-traffic --install` 与独立 `portbw` 均在落地机分别管理，不能把 HY2 VPS 上的 UDP/443 或临时节点端口作为 SOCKS5 本机 TCP 端口使用；两种协议在同一个仓库出现，不代表它们共享用户数据库或自动转发链路。

### 3. 每日流量与管理入口

```bash
socks5-traffic --install
socks5 list
socks5 status
```

每日统计独立开启；[账号/日志查询](#socks5-query)、[创建](#socks5-create)、配额和限速分别使用本 README 对应命令。运行数据位于 `/etc/socks5-manager/` 与 `/var/lib/socks5-manager/`，包含凭据，备份及审计原始日志不要公开。

</details>

<a id="maintenance"></a>

<details>
<summary>6.6 HY2 / WG-NAT / NAT / 每日统计的更新方法</summary>

> **更新范围必须区分：** `hy2.sh` 只更新 HY2 管理组件，不自动更新 Hysteria 核心、VPS WireGuard、NAT 机 `nat.sh` 或通用 `portbw`。GitHub `main` 变化不会自动改动已安装 VPS。生产环境优先使用确认过的提交版本，升级前保存可恢复的 VPS 快照。

#### HY2 VPS：更新管理工具

在**需要更新的 HY2 VPS** 下载同一仓库版本，并检查 Bash 语法后再更新（保留既有主节点配置、节点状态和凭据；仍建议先做 VPS 快照）：

```bash
curl -fsSL --retry 3 'https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/hy2.sh' -o /root/hy2.sh && chmod 700 /root/hy2.sh && bash -n /root/hy2.sh && bash /root/hy2.sh
```

需要重新应用主配置或**显式**升级 Hysteria 二进制时，回到上面的[6.1 主节点步骤](#hy2-install)。仅刷新管理组件不应当自动切换正在运行的核心版本。

#### HY2 VPS：更新每日流量统计

```bash
curl -fsSL --retry 3 'https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/traffic.py' -o /root/hy2_traffic.py && python3 -m py_compile /root/hy2_traffic.py && python3 /root/hy2_traffic.py --install
hy2_traffic
```

只更新统计模块，无需删除历史数据或重建节点。

#### HY2 VPS：更新 WireGuard / NAT 临时节点工具

这些脚本**只在 HY2 VPS** 执行，不是 NAT 出口机的更新。WG 脚本可能调整路由与接口配置；已经正常运行时，不要为对标而盲目覆盖，确实需要升级再安排维护窗口：

```bash
curl -fsSL --retry 3 'https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/vpswg.sh' -o /root/vpswg.sh && chmod 700 /root/vpswg.sh && bash -n /root/vpswg.sh && bash /root/vpswg.sh
curl -fsSL --retry 3 'https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/natjichang.sh' -o /root/natjichang.sh && chmod 700 /root/natjichang.sh && bash -n /root/natjichang.sh && bash /root/natjichang.sh
```

更新后用 `wg_nat_healthcheck.sh` 与 `natjichang.sh check` 核实；现有 Peer 公钥、AllowedIPs 与 NAT 映射必须保持正确。

#### NAT 出口机：沿用已验收的 jieshu，禁止 HY2 覆盖

**你现有的 `jieshu` NAT 不需要升级或重装来支持 HY2。** 以后确有 NAT 管理器升级需求时，按照 **`jieshu` 原仓库 README 的 6.6** 和它自己已验收的管理流程执行。不要在该机下载 `hy2jieshu/nat.sh`，不要执行 HY2 版本 `init`，也不要为 HY2 节点安装第二套探测 timer。

#### 通用 portbw：单独的受管理更新流程

`portbw.py` 与 `portbw-install.sh` 在 `jieshu` 和 HY2 仓库源码完全相同。已经安装的受管理版本使用上面 [6.4 portbw 安装与升级](#portbw-install) 的 `preflight-upgrade → upgrade → verify`，**不可在已有版本上重新执行首次安装 `install`**；不需要为 HY2 再开发、重测通用限速算法。

</details>

**各组件的更新范围：** HY2 管理器、每日流量、portbw、WG/NAT、独立 SOCKS5 分别有自己的更新入口和状态目录。仅更新 `hy2.sh` 不意味着应修改共享生产 NAT Peer 或强制升级 SOCKS5；单独更新脚本前先核对版本和已保存状态。新部署与已有业务机器必须区分：`install` 可能初始化服务，`update`/`upgrade` 可能重启已有业务，`check`/`audit` 通常负责检查但也应先核实实际脚本接口。

<a id="abuse-install"></a>

<details>
<summary>6.7 HY2 访问与异常审计：独立安装和实时 Stats API（可选）</summary>

在 HY2 VPS 以 root 安装只读命令；**不会重启 Hysteria、修改服务配置或启动后台采集器**：

```bash
curl -fL --retry 3 https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/hy2-abuse.py -o /root/hy2-abuse.py
python3 -m py_compile /root/hy2-abuse.py
install -m 755 /root/hy2-abuse.py /usr/local/sbin/hy2-abuse
PORT=40020 DAYS=7 hy2-abuse
hy2-abuse 40020 --days 7 --json
```

可选：**只有你已在 Hysteria 配置里自行启用 `trafficStats`、并仅监听本机回环地址**时，才能额外读取当前 TCP 连接目标：

```bash
# secret 文件路径为示例，务必 600 权限且由 root 保管
hy2-abuse 40020 --days 7 \
  --stats-url http://127.0.0.1:9999 \
  --secret-file /root/hy2-stats-secret
```

本程序不会代你创建 API 服务或暴露公网端口，也不保存 API 密码。只允许字面量 `127.0.0.1` 或 `[::1]`，拒绝远程地址、HTTP 跳转和代理转发。使用 `--secret-file` 前，需确保该文件与配置中的 API secret 一致且为 root 私有。

`/online` 和 `/dump/streams` 返回的是**当前**在线与 TCP 流，不是 7 天的访问域名历史；`DAYS` 只作用于 journald 异常事件。不要把这个工具的汇总当作自动处罚依据。

</details>

<a id="backup-recovery"></a>

<details>

<summary>备份位置与回退方法</summary>

操作前建立可恢复的整机快照。GitHub ZIP 不包含运行中的节点、内核规则和流量状态。

| 组件 | 默认位置 | 说明 |
|---|---|---|
| HY2 主节点及证书 | `/etc/default/hy2-main`、`/etc/hysteria/` | 包含密钥 |
| HY2 配额/IP/节点状态 | `/var/lib/hy2/` | 包含节点密码 |
| WireGuard | `/etc/wireguard/` | 两端分别备份，包含私钥 |
| portbw | `/etc/portbw/`、`/var/lib/portbw/`、`/var/lib/portbw-resident-release/` | 独立的限速配置和备份 |
| SOCKS5 独立落地机 | `/etc/socks5-manager/`、`/var/lib/socks5-manager/` | 只在可选 SOCKS5 落地机备份，含账号密码与使用状态 |
| 日志与验收证据 | `journalctl`、本机 root 私有验收目录 | journald 可轮替，日志范围不等于永久完整历史 |

<details>

<summary>受管理 portbw 专用回滚</summary>

```bash

bash /root/portbw-install.sh rollback

```

仅适用于当前安装器认可的托管记录和有效备份；回滚后仍需执行 `portbw audit` 和客户端连接测试。

</details>

</details>

**恢复与更新的安全边界：**

1. 更新前先创建服务商控制台能够实际恢复的整机快照；GitHub 源码备份不等于服务器业务状态备份。
2. HY2 主节点、受管理临时节点与证书、配额/IP 元数据分别备份，确认私钥和账号资料只保存在 root 私有目录，不要提交到 GitHub。
3. 通用 `portbw` 的 `rollback` **只针对安装器识别的受管理版本**，与 HY2 核心回滚、SOCKS5 更新回退无关；不要错误地用一个组件的恢复命令处理另一个组件。
4. SOCKS5 原安装器不提供通用 `uninstall` / `rollback`；涉及生产账号和日志变更，应使用预先验证的整机快照恢复，不能用旧脚本盲目覆盖。
5. 核心或组件恢复后，应先核对规则、服务及真实客户端；保护规则缺失时应维持 fail-closed，不应为恢复连接而临时开放全部来源。
6. 已完成的 Debian 13 真机测试与历史可复用证据见[本轮验收](#acceptance)，未测的真实 CA 续期、IPv6、72 小时/30 天长周期及异常断电仍应明确标记，不因 README 改写而变为“已通过”。

<a id="release-notes"></a>

<details>

<summary>版本说明与看门狗运行规则</summary>

旧测试机在 2026-11-04 Debian 13 真机已验证 HY2 主/临时节点、双向配额、来源 IP 限制、到期清理、WG-NAT 出口、断线防泄漏、VPS 重启恢复和 `portbw` 静态 10/10 Mbps。通用 portbw 的自动触发与恢复复用 `jieshu` 同源码历史验收；旧记录不代表当前 VPS 的端到端持续吞吐已经测试。

首次安装后配额重启归零问题由 [首次关机保存修复](https://github.com/liucong552-art/hy2jieshu/commit/893bb2dc25cc96bd7076849385d79ebefd730952) 修复；通用 portbw 与 jieshu 源码一致，由 [通用 portbw 引入提交](https://github.com/liucong552-art/hy2jieshu/commit/ab009ef736dc77c3cf6cf00f724867902ae89c04) 原样引入。

### 看门狗与生产运行规则

- **HY2 临时节点 Watchdog 72 小时宽限：** 第三次连续恢复失败后，才开始一次持久化的 72 小时宽限期。系统重启/手工重启服务不重置 `WATCHDOG_GRACE_START_EPOCH`；只有服务、端口监听、全部配额/IP 防护，且 NAT 节点的 WG 路由/握手均被重新核实为健康，才清空失败次数和宽限计时。
- **宽限期间仍然 fail-closed：** 若缺失 nft 防护，停掉监听并保留节点；若 WG 无有效握手，恢复失败的 NAT 节点不允许继续监听，不能改走 VPS 公网。
- **到期处理：** 自然 TTL 到期按原规则正常删除；72 小时宽限结束后，只有再次恢复失败且本次启动已稳定至少 300 秒，才执行最终节点清理。这与 `jieshu` 的持久宽限理念一致，但**尚需在专用临时节点上做跨重启/超过 72h 或模拟时钟的验收**，GitHub CI 不等于真实故障链路。
- `portbw` 是共享组件；HY2 节点删除/到期只清理对应端口策略，失败保留元数据供重试，其他端口不受影响。
- `nat.sh init/add/del` 可能重启 NAT 机 WG，影响其他 Peer。

</details>

### 与原 README 对应的日常操作闭环

以下顺序是**阅读指引**，不是建议对生产服务器自动执行的一串命令。`jieshu` 的查询、节点管理、配额/IP、暂停/黑名单、SOCKS5、WG/NAT 与限速说明分别在 HY2 的相同章节找到对应入口；对于协议不同或功能尚缺的项应按实际说明执行。

1. **查询**：先查 `hy2_audit.sh`、`pq_audit.sh`、`hy2_doctor.sh --strict`，再选读按端口的流量、来源槽位、自动降速与异常审计。
2. **创建**：明确普通还是 NAT 临时节点；设置 TTL、上传下载合计配额及来源 IP 数；创建后核对唯一 TAG、链接和真实客户端。
3. **修改**：区分清零重设 `pq_add.sh`、保留周期的 `pq_keepcycle.sh`、IP 槽位、portbw 聚合 Mbps。本 README 另提供利用现有 HY2 配额库的一行“本期剩余调整”操作（尚未真机验收，见第三章）。
4. **故障排查**：先查服务、UDP 监听、TLS/SNI、QUIC、证书、配额和黑名单；NAT 加查 Peer/握手/mark 路由。不要为了恢复而全局清空 nftables。
5. **暂停/删除**：`hy2-guard` 的暂停和封禁作用于目标端口 TCP+UDP，`forget` 只清该端口手工防护，节点到期/删除才清相应受管生命周期资源。
6. **安装/维护**：HY2 VPS 安装 HY2/必要时 WG，独立落地机手动安装 SOCKS5，已有生产 NAT 原样复用；各组件分开升级并保留安全回退手段。

<a id="acceptance"></a>
### Debian 13 真机验收与 `jieshu` 功能对标

**当前新机与旧证据分开记录。** 本轮为 2026-11-15 全新 Debian 13 VPS，实际测试、修复、未完成项见 [TASK_PROGRESS.md](TASK_PROGRESS.md) 及其中链接的当次验收报告。下文 2026-11-04 / 05 的结果均来自旧测试机，不自动计入本轮通过。

**本轮真机验收：** [2026-11-15 新机报告](tests/REAL_MACHINE_ACCEPTANCE_2026-11-15.md)记录正式 TLS、Windows 官方客户端主/临时节点、双向 SHA256、UDP、真实配额耗尽/恢复、IP 槽位、TCP + UDP 暂停/来源 IP 及 `/24` 封禁、静态限速、Watchdog 故障恢复、安全停止、删除/端口复用和 90 秒自然到期通过。

普通与 NAT 两节点保留数据卸载/重装、注册的证书 reload hook、回环 Stats API 只读审计均完成真实客户端联调；两次整机重启中，普通及 NAT 精确流量/配额字节保留，NAT 握手后外部下载、上传与 UDP DNS 恢复通过。生产 NAT 未重启，临时 Peer、timer 与私有测试工具已清理，原两枚 Peer 及配置精确恢复。通用自动降速算法复用 `jieshu` 同源码证据。

`--purge --remove-core` 的数据/核心移除、共享策略隔离与正式主节点新装已分别真机通过，最终Windows客户端出口正确，严格doctor为**0错误0警告**，审计退出0；安装的Hysteria2.14.0 Linux amd64核心与官方发布SHA256清单核对后固定。生产NAT及本机测试资源均已清理，最终保留主节点与可选工具，Linux166项测试通过。IPv6因本机无全局地址且域名无AAAA未测；实际72小时/30天、真实CA续证、跨版本及运行期失败升级回滚、异常断电和生产NAT重启未测；接续已补充SHA拒绝后回滚的真机通过记录。证书reload hook成功不等于真实续证已经发生。完整功能对标表与限制见[本轮报告](tests/REAL_MACHINE_ACCEPTANCE_2026-11-15.md)。

| 状态 | 判定依据 |
|---|---|
| 当前真机通过 | 当次报告记录实际执行、观察结果与清理；监听或配置检查不能代替客户端连通 |
| 复用已有证据 | 源码一致、依赖与适用条件一致，并明确原证据来源；新 Peer 连通仍须单独检查 |
| 仅自动化测试通过 | 单元测试、语法、生成脚本或模拟环境；不声称公网 UDP / TLS 已通过 |
| 尚未验证 | 缺少环境、凭据或长期等待；保留具体边界及后续条件 |
| 不适用 | VLESS Reality 密钥 / UUID 等其他协议专属逻辑；SOCKS5 作为独立可选模块提供 |

下面是**旧测试机历史摘要**：

[**完整实测记录：2026-11-04 Debian 13**](tests/REAL_MACHINE_ACCEPTANCE_2026-11-04.md)详细列出每个步骤、通过依据和未测试项。实测包括：普通临时节点及双向配额、来源 IP 上限、到期清理；一次真正发现的**首次关机配额持久化问题**（已通过 [首次关机保存修复](https://github.com/liucong552-art/hy2jieshu/commit/893bb2dc25cc96bd7076849385d79ebefd730952) 修复）；WG-NAT 客户端真实出口、断线阻断、恢复及整机重启后配额保留。

收尾时 `hy2_doctor.sh --strict` 为 **0 错误、1 警告**；警告是未设置 Hysteria 二进制 SHA256 校验。NAT 节点刚启动时允许因 WG 握手未就绪而安全拒绝监听，随后自动重试成功；不应把这一启动时序当作持续故障。

### `jieshu` → `hy2jieshu` 逐段适用性对照索引

母版以 `jieshu` 的 `f21b70d0` 版本为参考，保留其章节顺序；**此表是内容对应与协议边界的索引，不是声称两个不同协议具备一模一样的底层实现**。

| jieshu 母版章节/锚点 | hy2jieshu 对应位置 | 内容转换或明确差异 |
|---|---|---|
| 1. 总览 / `#queries` | [查询与检查](#queries) | 节点审计、配额/IP、限速/日志、WG、SOCKS5 独立落地 |
| 1. `#advanced-queries` | [补充查询](#advanced-queries) | 同一配额快照、核对本机限速、握手/路由 |
| 1. `#socks5-query` | [SOCKS5 查询](#socks5-query) | 原样复用成熟 SOCKS5 命令；运行在落地机 |
| 1. `#node-link` | [节点链接](#node-link) | `vless://` 改为 HY2 节点链接及凭据文件 |
| 1. `#active-ips` | [来源 IP/UDP](#active-ips) | UDP/IP 槽位，不照抄 VLESS TCP established |
| 1. `#daily-traffic` | [HY2 每日流量](#daily-traffic) | 用 HY2 UDP 计数器与相同按日查看体验 |
| 1. `#speed-logs` | [自动降速日志](#speed-logs) | 同源 portbw 事件、端口/上行下行分离 |
| 1. `#vless-audit` | [HY2 异常审计](#hy2-audit) | 现有 journal 警告、来源槽位、可选当前 TCP 目标；不伪造历史访问域名/UDP |
| 1. `#socks5-daily` / `#socks5-access` | [SOCKS5 每日流量](#socks5-daily) / [访问审计](#socks5-access) | 原成熟源码可选，按实际日志保留时长查询 |
| 1. `#subscription` | [临时节点订阅](#subscription) | 生成文件包含敏感 HY2 节点链接，不含主节点 |
| 2. `#temp-create` | [临时节点创建](#temp-create) | 秒、分钟、小时、天、固定端口、IPv6、普通/NAT |
| 2. `#socks5-create` | [SOCKS5 创建](#socks5-create) | 落地机分钟/小时/天/端口/公网映射 |
| 3. `#quota-ip` | [配额/IP 修改](#quota-ip) | 已用清零、总配额与 IP 槽位均按 HY2 状态操作 |
| 3. `#quota-keep-cycle` | [保留周期重设](#quota-keep-cycle) | HY2 已有独立保留周期脚本，**不是追加余额** |
| 3. `#quota-set-current-remaining` | [本期剩余额度差异](#quota-set-current-remaining) | 使用 HY2 现有配额库提供独立的一行操作；不新增安装脚本；仅模拟验证，未进行真机验收 |
| 3. `#quota-reset-time` | [重置时间](#quota-reset-time) | 读取 HY2 quota 元数据，不执行系统修改 |
| 3. `#portbw` | [静态/自动限速](#portbw) | 同源码通用 portbw；HY2 UDP 与端口 TCP 共享限额 |
| 4. `#trouble-guide` | [故障排查](#trouble-guide) | HY2 UDP/TLS/QUIC、系统服务、WG 防泄漏、guard |
| 5. `#pause-port` | [暂停](#pause-port) | 使用 HY2 guard，作用于同数字端口 TCP+UDP |
| 5. `#source-blacklist` | [来源黑名单](#source-blacklist) | IP/CIDR 封禁、逐条批量管理、独立恢复 |
| 5. `#blacklist-report` | [黑名单状态](#blacklist-report) | `hy2-guard status` / `audit`，不复制 VLESS 规则 |
| 5. `#node-manage` | [节点清理](#node-manage) | 只清当前受管临时节点，端口回收与元数据安全清理 |
| 6. `#install` | [安装与更新](#install) | 每项先说明在哪台机器执行以及影响范围 |
| 6. `#vless-install` | [HY2 主节点部署](#hy2-install) | 正式 TLS、Hysteria 核心、`hy2.service`、UDP/443 |
| 6. `#wg-nat` | [WG/NAT 五步](#wg-nat) | 新 HY2 VPS 加独立 Peer；已验收生产 NAT 不覆盖 |
| 6. `#daily-install` | [HY2 每日统计安装](#daily-install) | 读写 UDP 每日历史并保持与总配额独立 |
| 6. `#portbw-install` | [portbw 安装更新](#portbw-install) | 同源安装器与静态/自动限速 |
| 6. `#socks5` | [SOCKS5 可选安装](#socks5) | 四文件同目录下载、原安装器哈希不变 |
| 6. `#maintenance` | [独立组件维护](#maintenance) | 已部署版本升级不等于重新初始化生产 NAT |
| 6. `#abuse-install` | [HY2 审计安装](#abuse-install) | 只读工具，官方 Traffic Stats 仅当前 TCP；不照搬 VLESS 内嵌脚本 |
| 6. `#backup-recovery` | [备份与回退](#backup-recovery) | HY2、WG、SOCKS5、portbw 各自保留独立状态与回退边界 |
| 6. `#release-notes` | [版本与看门狗](#release-notes) | HY2 fail-closed、72h 宽限语义和实际验收边界 |

**不适用项说明：** VLESS Reality UUID/密钥、Xray inbound 命令及 VLESS 审计脚本不能当作 HY2 命令。审计历史缺失属于协议与可用日志来源差异；“本期临时剩余额度调整”已提供基于现有库函数的 Bash 一行操作，但并非主安装器内置命令，且尚未真机验收。此表不表示已做新的真机测试或已经覆盖母版全部场景。

<a id="feature-gap"></a>
### 与 `jieshu` 的共享能力、HY2 专属适配及遗留差距

[**完整代码复用审计（2026-11-05）**](tests/SHARED_COMPONENT_AUDIT_2026-11-05.md)：精确 Git Blob SHA、NAT/WG 差异、端口统计与配额适配，以及哪些验收不需要重复。两个项目始终分机部署，技术审计中提到的同机路径冲突**不是本项目的发布阻塞项**。

| 功能 | `hy2jieshu` 当前状态 | 推荐处理 |
|---|---|---|
| Hysteria 2 主/临时节点、配额、IP 限制、到期管理 | 当前新机真实客户端、配额耗尽/恢复、来源槽位、删除复用与自然到期通过 | 普通/NAT保留数据重装、purge/core删除和新装已分别通过；最终主节点客户端及严格doctor通过 |
| WG-NAT 出口、防泄漏与恢复 | 当前新 VPS / 新 Peer 外部双向 TCP 与 UDP、停 WG 断流、握手恢复及新机重启恢复通过 | 原生产 NAT 配置精确恢复且无测试残留；生产 NAT 机未重启 |
| 按端口每日流量历史统计与导出 | **已移植并真机验证**：HY2 UDP 双向字节、原配额一致、正常重启前后保留且 0 字节重复计数 | 剩余：跨北京时间午夜、突然断电、30 天裁剪及端口复用 |
| 静态端口限速、持续流量高峰自动降速（`portbw`） | **两个仓库的 `portbw.py` / `portbw-install.sh` Git Blob SHA 完全相同**；`jieshu` README 记录 Helan 实际上传/下载触发与恢复，HY2 本机通过静态测速和自动策略空闲生命周期 | **直接继承已验收的通用内核限速算法**；额外 HY2 全链路高负载仅作可选集成测试，不再强制重复 |
| 端口暂停、来源 IP/CIDR 黑名单 | **真机通过**：端口暂停/恢复、来源 IP `/32` 和 CIDR `/24` 封禁/解封；独立 nft 表正常重启持久化，HY2/WG 均正常 | 本轮真实90秒自然到期已清理端口guard/限速；异常断电仍未测 |
| 访问目标、共享嫌疑、异常连接审计 | `hy2-abuse.py` 提供来源槽位、异常事件和可选当前 TCP 目标；本轮回环 Stats API 实际读取到在线实例、TCP 流及非空目标汇总 | 不把在线实例当人数，不宣称提供历史目标、UDP 目标或自动处罚结论 |
| NAT 端 `probe-once` / `probe-enable` / `probe-disable` / `probe-status` | 既有 `jieshu` NAT 与 Peer 探测由操作者确认已真机验收；HY2 版本复制了相同机制但管理前缀不同 | **直接复用 `jieshu` NAT，不部署 HY2 NAT 管理器，不重复 Peer 验收**；NAT 实际冷重启属于单独破坏性测试 |
| 独立 SOCKS5 账号 / 统计 / 审计 | 原样复用 jieshu 成熟模块，独立落地机手动安装，HY2 入口不自动安装 | 复用上游验收，本轮不重测；TCP CONNECT，不支持 UDP ASSOCIATE |
| VLESS Reality 特定管理 | 非 HY2 协议能力 | 不复制 Reality 密钥、UUID 或 Xray 专属配置 |

`vpswg.sh` 是对 `jieshu/vpswg.sh` 的 HY2 适配版：大部分代码相同，但临时节点目录、锁和旧标记切换时的 fail-closed 保护不能直接替换回 VLESS 版本。旧机已有 VPS 重启记录；本轮另行完成当前新 VPS 的真实 NAT 出口、测试 VPS WG 停止阻断与握手后恢复，不代表所有版本混用或生产 NAT 冷重启均已通过。

对标目标是达到类似的管理体验和验证标准，不承诺把其他协议模块直接塞进 HY2。新增或修改的行为须完成相应 CI 与必要真机回归，未验证项保持明确状态。

#### README 与 `jieshu` 的对标判定口径

| 对标层面 | 本项目的处理方式 |
|---|---|
| 六章顺序、导航、折叠操作、查询与故障步骤 | 以 `jieshu` 的阅读顺序组织；命令示例必须是本仓库实际提供的入口 |
| VLESS/Reality 主节点与临时节点 | 替换为真正的 Hysteria2 TLS/QUIC、UDP 监听、密码认证与 HY2 生命周期管理 |
| 配额/IP 限制/日统计/防护/看门狗 | 保留管理体验，但运行时的 UDP 元数据、nft 规则和服务名必须按 HY2 适配 |
| SOCKS5 / portbw | SOCKS5 四源码及原审计测试与上游完全一致、作为独立落地机可选组件；通用 portbw 复用相同内核实现 |
| WG/NAT 出口 | 复用 `jieshu` 已验收 NAT 端，HY2 VPS 只配置自己的 WireGuard Peer 和 HY2 临时节点 |
| 访问目标与滥用审计 | HY2 提供来源槽位、journal 异常统计及可选的当前 TCP 流目标；未实现完整历史域名/UDP 目标时如实说明 |
| 验收来源 | 当前 VPS、旧机与 SOCKS5 上游分别归档；本次文档修改**不会**自动验证新的业务场景 |

**明确保留的协议差异：** VLESS Reality 的 UUID、公私钥、Xray inbound/TCP 检查不是 HY2 的配置；SOCKS5 独立账号不等于 Hysteria2 认证用户；Hysteria2 的 UDP/QUIC 也不能被描述成 SOCKS5 UDP ASSOCIATE（上游 SOCKS5 本身只实现 TCP CONNECT）。

<details>
<summary>历史验收与旧测试工具（旧主机，不代表当前 VPS）</summary>

- [2026-11-04 至 2026-11-05 原始验收记录](tests/REAL_MACHINE_ACCEPTANCE_2026-11-04.md)：旧主机真实客户端、配额、IP 限制、WG-NAT、防泄漏与正常重启。
- [共享组件复用依据](tests/SHARED_COMPONENT_AUDIT_2026-11-05.md)：同源码 portbw、NAT 适用条件及 HY2 专属差异。
- [旧批次工具与执行说明](docs/LEGACY_ACCEPTANCE_GUIDE.md)：保留旧 `helan` 的 12 / 9 / 14 / 6 项批次结果、失败后修复与清理记录。批次中重复的健康检查不计为独立功能数量。

旧工具具有主机保护和 WG-NAT 前提；不要为了在新机凑出 PASS 而改掉保护、跳过依赖或替换断言。缺少外部 NAT、全球 IPv6 或真实客户端时，相应场景须记为未验证。

</details>

### 适用边界与安全

- 只面向全新机器
- 不迁移旧 Hysteria、旧 WireGuard 或旧 nftables 状态
- 主节点固定为 IPv4 UDP `443`
- 卸载前先备份所需配置及统计，按[卸载说明](#uninstall)执行
- 不应与其他会频繁重建相同 nftables、iptables 或策略路由的管理脚本混用
- 投入业务前，验证当前机器的真实客户端连接与所用保护组件；长期专项按报告保留状态

仅在自己拥有或已获明确授权的服务器和网络上使用，并遵守当地法律和服务商条款。

- 本次只验证 Debian 13 的指定服务器与客户端条件，不代表所有系统和网络已通过。
- 任何 `hy2://` 链接及 `/etc/wireguard` 密钥均视为敏感凭据，不应放入 GitHub、公开问题单或原始验收日志；公开记录采用匿名摘要。
- 临时节点到期自动回收；文中 `40020` 等均为示例端口，需换成实际端口并确认节点归属。

---

本文直接下载入口指向 `liucong552-art/hy2jieshu`；原样 SOCKS5 安装器的远程 fallback 仍为 `jieshu`，按6.5下载四文件可使用配套本地模块。HY2 与独立 SOCKS5 各用自己的账号、配额和统计入口，共享 portbw 单独管理；VLESS Reality 密钥等协议专属配置不属于 HY2。
