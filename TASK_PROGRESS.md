# HY2 对标与新 VPS 验收进度

更新时间：2026-11-15（北京时间）

## 当前范围
- 唯一可写/可推送仓库：liucong552-art/hy2jieshu；jieshu 仅只读对照。
- 起点：0b85ce3；本轮为全新 Debian 13.5 专用 VPS，SSH 和两端 DNS A 查询均成功。
- 不提交真实节点凭据、私钥、邮箱配置或原始部署日志。

## 已完成与依据
- [本轮阶段验收](tests/REAL_MACHINE_ACCEPTANCE_2026-11-15.md)：正式 ZeroSSL TLS / Hysteria 2.14.0、外部 Windows 客户端、主/临时节点双向 SHA256、UDP echo、错误密码/SNI拒绝、真实配额耗尽/恢复、IP槽位、TCP+UDP暂停/来源封禁通过。
- portbw 保持 jieshu 同源码，自动降速算法复用原证据；新机安装、静态10/10 Mbps、同端口TCP/HY2与重启集成通过。
- 真实 reboot 后 SSH 重连，主/临时节点和管理组件恢复；daily上/下行及配额保存字节前后精确一致，guard与限速恢复。
- 本机 watchdog 真实stop→恢复后外部SHA256/UDP再通；删除暂停/封禁/限速节点时meta、guard、portbw全清，同端口重建成功。
- guard表丢失恢复pause；配额/IP表受控删除后恢复（新节点已用0）；隐藏guard CLI时watchdog非0并停主/temp、保留meta，归还并恢复防护后外部SHA256/UDP通过。
- 真实90秒TTL自然到期，meta/portbw/guard自动全清。现有NAT经授权临时追加独立Peer，生产WG及原2Peer不变；新VPS真实出口、下载/上传/UDP DNS、停WG断流且主节点可用、握手后恢复均通过。
- 保留数据卸载/重装最终整链路通过：普通+NAT unit各600备份，guard/NAT helper保留，防护恢复后main/local/NAT正常，原限速与无关端口策略保留，外部三节点复测通过；真实调用acme-reload及客户端回归通过（不算真实CA续期）。
- 第二次真实reboot包含NAT节点，daily down653509/up302685与quota956194字节前后精确一致；SSH/main/local/WG恢复，NAT握手前安全拒绝，握手就绪后watchdog/health/service通过，最后一轮外部业务待结果。真实来源/24封禁下TCP+HY2阻断、相邻端口正常、clear恢复已通过。
- README/docs 下载源、六章/折叠/命令对标与卸载入口已保存；`0eedd49`已推main，CI run43690417997成功；最新Linux快照166项测试通过，后续修改须最终回归。

## 下一步与未验证
- 报告保留首次重装acme即时reload/unit缺失失败、临时unit缺失被GC误判失败及根因；修复后keep完整重跑已通过，勿再当待测或删除失败历史。
- 下一步：核实第二次reboot后的最后一轮外部NAT业务结果，随后purge/重装与最终回归；166项Linux测试已通过。
- **收尾必须核实清理生产NAT临时Peer及其1小时自动清理timer**（已设兜底不等于已清理）；不改既有Peer、不init/重启生产WG。
- IPv6、实际72小时/30天、真实续证、异常断电、生产NAT重启未测。
- IP槽位第二来源是VPS回环，非第二台公网设备；本机没有重复通用portbw自动触发压测。

## 接续要求
- 先读本文件、git log 和本轮验收记录，确认当前实际状态后继续。
- 只把本轮实际执行的场景记为新机通过；不要重跑已通过且代码未变化的测试，不公开NAT地址、公钥/私钥或来源IP。
- 重要阶段提交推送；尚未验证部分应明确保留。
