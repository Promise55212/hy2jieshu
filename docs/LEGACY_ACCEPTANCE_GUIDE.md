# 旧测试机验收工具与执行记录（2026-11-04 至 2026-11-05）

本文归档 README 原有的 `helan` 测试说明，供追溯既有结果。它们不是 2026-11-15 新 Debian 13 VPS 的测试结果；旧批次脚本有主机名及 WG-NAT 前提，不能直接当作任意新机的验收入口。新的真实执行记录以 [TASK_PROGRESS.md](../TASK_PROGRESS.md) 指向的当次报告为准。

原始证据见 [历史真机记录](../tests/REAL_MACHINE_ACCEPTANCE_2026-11-04.md) 与 [共享组件审计](../tests/SHARED_COMPONENT_AUDIT_2026-11-05.md)。历史 PR 号属于当时的来源，不表示当前仓库有相同编号的 PR。

### 一键批量真机回归（仅 `helan` 测试机）

以前每项单独复制命令的验收方式已新增自动化：`tests/hy2_batch_acceptance.py`。在 **Debian 13 测试机 `helan`**、root 下运行一次，即可自动完成既有服务、doctor、systemd timers、北京时间流量 JSON、WG 打标路由、只读异常审计，以及一枚**新生成、独立、随机名**的 NAT 临时节点的端口 pause/resume、文档 IP `/32` 与 CIDR `/24` 封禁/解封、nft guard `restore`、30 天周期配额保持测试与资源清理。源 IP 封禁只使用 `198.51.100.7/32` 和 `203.0.113.0/24` 文档保留网段，不封真实客户端。普通业务节点不作变更。

```bash
curl -fsSL --retry 3 \
  https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/tests/hy2_batch_acceptance.py \
  -o /root/hy2_batch_acceptance.py && \
python3 -m py_compile /root/hy2_batch_acceptance.py && \
python3 /root/hy2_batch_acceptance.py --live
```

完成后终端打印各项 `PASS` / `FAIL` / `SKIP`、`FINAL_RESULT`、`CLEANUP` 和本次 `/root/hy2-batch-accept-*/report.json` 的准确路径。**仅分享该脱敏 JSON 报告**，不要上传测试目录内的 `*.raw.log`：创建日志包含测试节点密码和 HY2 链接。测试器退出时自动清理节点和专用 nft 规则；同时在运行前先安装**跨重启仍有效、30 分钟后执行一次**的 systemd cleanup 安全计时器。正常清理成功时连同计时器一并移除；遇到清理错误时保留计时器兜底，终端会提示。根目录下仅留脱敏报告和 root 私有原始审计日志。

不带 `--live` 时仅执行只读自检，不会创建节点：`python3 /root/hy2_batch_acceptance.py`。脚本明确拒绝在非 `helan` 的机器上执行，且从未自动重启 VPS、NAT 出口机或 WireGuard。自动化规则检查**不能替代**前面已完成的 v2rayN 真实断网/恢复证据；异常断电、真实 30 天事件、IPv6 与跨机故障注入仍需单独隔离验收。本脚本 GitHub Actions 单元测试通过并不等于实际 VPS 验收，须以脚本在真实 `helan` 的 `report.json` 为准。

**2026-11-05 首次批量真机执行通过**：`helan` 控制台记录 12 项 PASS、0 FAIL，包含独立测试 NAT 节点创建、文档源网段封禁/解封、保留 30 天锚点的配额重设及自动删除；末尾 `FINAL_RESULT=PASS`、`CLEANUP=PASS`。此结论依据操作者控制台记录，未另行收取 `report.json` 本体，也不等同于客户端断网测试或重启故障注入。


### 第二轮一键自动维护验收（`--maintenance`）

和第一轮 `--live` 不同，第二轮集中检验 **节点真实到期清理、Watchdog 健康巡检与 `portbw` 自动限速策略的空闲态配置/审计/撤销**，而不是重复已经验收过的暂停、配额重设。

在 **仅允许 `helan` 的测试机**用下面一条命令运行：

```bash
curl -fsSL --retry 3 \
  https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/tests/hy2_batch_acceptance.py \
  -o /root/hy2_batch_acceptance.py && \
python3 -m py_compile /root/hy2_batch_acceptance.py && \
python3 /root/hy2_batch_acceptance.py --maintenance
```

此模式先完成主服务、doctor、WG、guard 和 timer 预检，再建立 **180 秒有效期**的随机 HY2-NAT 临时节点，检查仅健康状态下的 Watchdog 巡检、尝试对其配置 `portbw auto` 基础 5/5 Mbps 与降速 2/2 Mbps 并做 audit/status/off/del，最后**等待真实 TTL 到期、服务和配额/IP 限制元数据自然清理**。所有创建动作前均安装 30 分钟后的一次性、跨重启持久安全清理 timer；失败或退出时立即强制清理本次拥有的资源。一次自然到期通常需等待约 3 分钟；若没能自然清理则记为 FAIL，不会将强制清理冒充通过。此模式绝不主动停止主服务或 WireGuard、不改生产机。

**测试范围界限：** Watchdog 只在没有其他临时节点时主动跑健康巡检，有其他节点会 SKIP，以免触碰其他测试或业务；故障恢复/连续三次失败后 72 小时宽限的真实故障注入**不在这轮**。`portbw` 仅在已安装、tc 模式启用、监控服务运行、且无其他受管端口策略的安全前提下执行；否则 SKIP，不会为了测试擅自安装或升级限速器。空闲态自动策略正常不等于**持续高流量真实触发降速与恢复已通过**；后者需单独受控压测。输出的 `report.json` 有每项 PASS/FAIL/SKIP 和清理状态，只分享脱敏 JSON，绝不分享 `*.raw.log` 或 HY2 节点链接。

### 第三轮一键自动边界测试：双节点、配额隔离和端口复用

第二轮已在 `helan` 通过 **9 项 PASS，0 FAIL，1 SKIP**：真实等待 180 秒节点自然到期，完成 portbw 空闲态自动策略配置、审计和撤销。Watchdog 健康扫描因现有其他临时节点被跳过，不计为通过；持续高流量降速、故障恢复仍需专项测试。

**第三轮曾发现测试器误判，现已修复并复跑通过（2026-11-05）：** 首次 `--edges` 使用 20 分钟节点却套用了 31 天的周期断言，出现 `FINAL_RESULT=FAIL`，但 `CLEANUP=PASS`；PR #25 修复为按节点期限判定。修复后在 `helan` 真机重新运行，得到 **14 PASS、0 FAIL、0 SKIP、`CLEANUP=PASS`**。旧失败结果保留用于回归记录。

第三轮现在提供 `--edges` 模式，**仅限 `helan` 测试机**，自动创建两个新随机命名 HY2-NAT 节点 A/B，核对它们有不同 UDP 端口、独立 `hy2_pq` 配额与 `hy2_iplimit` 来源槽位规则、各自每日统计 JSON；暂停 A 后确认 B 没有被暂停，重设 A 配额后检查 B 的配额所有权、额度与 30 天锚点没变；强制删除 A，检查 A 的配额/IP 限制元数据和 nft 对象都消失、B 仍存活；最后使用旧端口创建 C 并确认新配额/所有权，最终删除 C/B/A、检查系统状态。只测试服务端规则与节点隔离，**不伪称两个客户端同时在线、真实用户流量竞争或 IPv6 连接已验证**。

```bash
curl -fsSL --retry 3 \
  https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/tests/hy2_batch_acceptance.py \
  -o /root/hy2_batch_acceptance.py && \
python3 -m py_compile /root/hy2_batch_acceptance.py && \
python3 /root/hy2_batch_acceptance.py --edges
```

此模式执行任何新建操作之前就启动 **3 个分属 A/B/C 的跨重启一次性 30 分钟安全清理 timer**。测试失败立即尝试清理，仅在对应节点和 nft 测试对象清洁后撤销该节点 timer，失败则保留定时兜底。它不会停止 HY2 主节点、重启 WG、操作生产机，也不会对其他测试节点执行删除；其他临时节点即使存在也不应影响本批次归属校验。完成后只分享 `report.json` 或其无敏感字段的汇总输出，**不要发原始 HY2 配置/URL、`*.raw.log`**。

### 常规收尾与剩余条件一键盘点

**第三轮修复后首次真机复跑已通过**（2026-11-05）：`--edges` 共 14 项 PASS、0 FAIL、0 SKIP、`CLEANUP=PASS`；A/B 并行节点、配额和 IP_LIMIT 隔离、A 删除、C 复用旧端口、最后 A/B/C 自动清理。原先短期周期误判由 PR #25 修复，不能再沿用“第三轮尚未通过”的旧描述。

在 **`helan`** 运行下面这条**只读**命令后，可立即生成汇总报告和剩余项目清单，不重新创建任何测试节点，也不会停止或重启服务：

```bash
curl -fsSL --retry 3 \
  https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/tests/hy2_release_gate.py \
  -o /root/hy2_release_gate.py && \
python3 -m py_compile /root/hy2_release_gate.py && \
python3 /root/hy2_release_gate.py
```

输出 `ROUTINE_GATE=PASS` 仅说明 **当前健康审计成功、且本机保存的 `--live`/`--maintenance`/`--edges` 三类批次曾成功并且清理完成**，不代表所有生产故障场景均通过。脚本读取 root 私有汇总文件、不分享原始 HY2 链接，写出脱敏的 `/root/hy2-release-gate-report.json`。有现存临时节点时不修改它们，也不会清理任何用户节点。

下一步**不重复常规功能回归**，仅安排三项专项：Watchdog 故障注入与恢复、portbw 实际高流量降速/恢复、NAT 端 Peer 探测；IPv6 仅在确认有全球 IPv6 和正确 AAAA 记录时测试。真实 30 天重置、证书轮换、异常断电属于持续或破坏性专项，应保持单独验收状态，不阻止已经通过的常规功能得到明确的结果。


### 第四轮加速专项：两台机器分别一条命令（不重复核心回归）

**A. 测试 VPS `helan`：真实 Watchdog 服务恢复。** 新 `--recovery` 模式仅在**没有其他受管临时节点**时才新建独立 `D=1200` HY2-NAT 临时节点，提前安装跨重启 30 分钟自动清理保护，人工故障注入被自动化为**只停止新测试节点的 systemd 服务**；验证实际停止状态后，启动受管理 Watchdog 并核对监听重新启动、配额/IP_LIMIT 防护、WG 和主 HY2 健康，最后删除临时资源。不会停止主节点、WG 服务、NAT 出口机或生产机；有其他临时节点则明确 SKIP，不强制破坏现存节点。

```bash
curl -fsSL --retry 3 \
  https://raw.githubusercontent.com/liucong552-art/hy2jieshu/main/tests/hy2_batch_acceptance.py \
  -o /root/hy2_batch_acceptance.py && \
python3 -m py_compile /root/hy2_batch_acceptance.py && \
python3 /root/hy2_batch_acceptance.py --recovery
```

**2026-11-05 真机补充：Watchdog 已通过 6 项 PASS、0 FAIL、0 SKIP、`CLEANUP=PASS`。** `helan` 上独立临时节点真实停止后，受管 Watchdog 成功重启并恢复；不会再把这一条当作待验证。**仍未验收**连续三次失败后的 72 小时宽限、底层 nft 全表清空或异常断电。

**B. NAT 出口复用（不需要另装 HY2 NAT，也不重复已验收的 `jieshu` NAT）。** `jieshu/nat.sh` 与 `hy2jieshu/nat.sh` 都以 WireGuard `wg-exit` + 默认 UDP/51820、NAT 端 `10.66.66.2/24`、IPv4 FORWARD/MASQUERADE 提供无关应用层协议的出口。现有 `jieshu` 出口已由操作者独立验收，`helan` 的 HY2 NAT 出口/断流阻断/恢复也已有真机证据，**不必重装、不必迁移、不必为了 HY2 重做 Peer 探测**。多 VPS 接入时，每台 VPS 的 WireGuard 公钥与地址（Peer 的 `AllowedIPs`）必须唯一，NAT 出口管理员须保证 Peer 映射正确。

两个项目的**管理脚本不完全相同**：`jieshu` 的 Worker/Timer 前缀为 `vr_wg_peer_probe.sh`、`vr-wg-...`，HY2 的为 `hy2_wg_peer_probe.sh`、`hy2-wg-...`。请勿在已部署 `jieshu` 的 NAT 机器上用 HY2 的 `nat.sh init/add` 代替现存实现，这类动作可能重启整个 WG，影响共享 Peer。

仓库保留 `tests/hy2_nat_peer_acceptance.py` 仅供**确有需要时**额外排查：已经改为**默认只读**，可识别这两个管理器前缀，只核对既有 Peer 文件、运行时 AllowedIPs 和 Timer 状态，**绝不启停或覆盖原有定时器**。显式指定 `--probe` 才对已安装 Worker 发送一包探测，且不写入 systemd 单元；`WG_PROBE_SENT` 不表示远端新握手成功。现有 NAT 已验收时不需要再执行这项可选检查。

**C. 通用 portbw 限速引擎不需要再次从头压测。** `jieshu` 上游已记录同一源码在 Helan 实测上/下行自动触发和恢复；HY2 与其 `portbw.py`、安装器及两份核心测试文件 Git Blob SHA 均一致，且 HY2 已通过本机限速配置/审计生命周期。**只有用户明确要求证明特定 HY2 链接的端到端持续吞吐**时，才额外安排受控客户端压力测试；不能在当前报告里冒充那项已经实测，也不能把它作为重复的常规发布门槛。

### 仍需后续实测的场景

下面是完整参考验收清单，**并非 12 项都已完成**；IPv6、30 天周期、NAT 机本身重启、真实续证、核心升级回滚、异常断电及 nftables 全表冲刷均未做完。

建议先在一台全新 HY2 VPS 和一台全新 NAT VPS 测试：

1. `hy2_doctor.sh --strict` 无错误
2. 主节点能导入 v2rayN 并连接
3. 主节点出口 IP 是 HY2 VPS
4. 普通临时节点能连接并按时间自动删除
5. 达到 `PQ_GIB` 后端口停止转发
6. 超出 `IP_LIMIT` 后新来源 IP 被拒绝
7. IPv6 临时节点可连接，IPv4/IPv6 不串入
8. WG-NAT 临时节点出口 IP 是 NAT 机
9. 停止 `wg-quick@wg-nat` 后，NAT 节点断流且不泄漏 VPS 本机出口
10. 清空 HY2 nftables 表后，watchdog 能恢复或停止节点
11. HY2 VPS 与 NAT 机重启后，Peer、路由、配额和临时节点状态恢复
12. 模拟证书续期后，主节点和未到期临时节点正常重载

