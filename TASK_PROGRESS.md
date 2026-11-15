# HY2 对标与新 VPS 验收进度

更新时间：2026-11-15（北京时间）

## 范围与保存
- 唯一可写仓库：liucong552-art/hy2jieshu；jieshu全程只读。起点0b85ce3，阶段提交0eedd49、432bf40已推main；两次CI run43690417997、43692194673成功。
- 当前全新Debian13.5/Hysteria2.14.0真实验收见[本轮报告](tests/REAL_MACHINE_ACCEPTANCE_2026-11-15.md)；最新Linux166项测试通过。不得上传真实地址、来源、公私钥、密码、邮箱或原始日志。

## 已完成
- 正式TLS、Windows官方客户端主/临时节点双向SHA256与UDP、错误密码/SNI拒绝、真实配额耗尽/恢复、IP槽位、TCP+UDP暂停与/32、/24封禁通过。
- portbw同源码算法复用jieshu证据；新机安装、静态限速、共享策略隔离通过。Watchdog真实stop恢复、guard失效/工具缺失安全停止及恢复、删除复用、90秒自然到期清理通过。
- 普通+NAT两节点保留数据卸载/重装完整复测通过；两次真实失败及修复根因保留在报告。registered reload hook与可选loopback Stats API真实客户端联调通过（不算真实CA续证）。
- 两次真实reboot；NAT daily/配额956194字节前后一致，握手后Windows外部下载SHA256/上传回显/UDP DNS全部通过。
- 生产NAT临时Peer已清理，配置精确恢复、原2Peer不变、WG全程未restart；1h timer inactive，私有helper/备份删除，测试VPS NAT节点cleanup0，无生产测试残留。
- purge/core删除退出0：HY2状态/env/core/link/四表及自有41000策略移除，无关41001保留，SSH/共享组件保留；manager与正式main重新安装退出0，发布raw源码cmp一致。
- README六章/导航/折叠、真实下载源、卸载与服务说明、完整功能对标表完成；旧helan说明归档，原始历史证据保留。

## 当前下一步与边界
- 最终Windows主节点curl0且出口正确、hy2-abuse443退出0、严格doctor0错误0警告通过；官方2.14.0 amd64 SHA核对后固定。4cc4faf与远程一致且CI run43693061619成功；Linux166项已通过。
- VPS测试策略、临时meta及测试监听已清；仅UDP443为HY2监听，guard0pause0ban、portbw空策略；测试WG停用/私有归档，Stats secret删除，生产NAT无残留。
- IPv6因VPS无全局地址/域名无AAAA未测；实际72小时/30天、真实CA续证、跨版本/运行期失败升级回滚、异常断电、生产NAT重启未测；SHA门禁拒绝后回滚已补真机通过。
- IP_LIMIT第二来源为VPS回环；丢配额表测试已用0；未重复portbw算法压测。HY2新NAT安装器修复、WG未来握手时间拒绝仅自动化/正常握手覆盖，未生产安装nat.sh或真机调时。

## 接续
- 先读本文件、最近git提交与本轮报告，再确认机器实际状态；已通过且代码未变的项目不重复测试。
- 保留失败和未测边界；仅把当前实际执行场景记为当前真机通过。重要进展及时提交推送。

## 保存时的补充交接

- 本轮修改及新增文件已做敏感信息排查；不提交原始私有日志、真实凭据或节点链接。
- 额外系统观察：测试 VPS 的 networking.service 因尝试启用不存在的 eth1 而失败；当前 eth0 默认路由、SSH 与 HY2 客户端均正常。当时未改动或重启网络服务；接续已安全修复并验证失败unit为0，详见后文。
- 按用户额度要求停止扩展工作；长期与未验证项保持上文状态，生产服务器不再执行写操作。

## 2026-11-15 接续
- 恢复检查：本地HEAD与远程main均为4cc4faf，工作区干净；对应CI run43693061619成功，既有验收不重复。
- VPS镜像残留eth1配置已安全修复：仅移除不存在eth1的两行配置，原文件保留root私有备份。eth0配置、地址、默认路由不变；双模式ifup预演确认无接口重配置后，仅start原failed oneshot，未stop/restart/ifdown/force。新SSH正常，networking/HY2/timers active，失败unit数0。
- README纠正guard绝对安全承诺；同数字端口TCP/UDP均受规则影响，不得复用SSH管理端口，双协议行为保持。
- 审查发现核心/主部署两层回滚会吞掉恢复失败并删除备份；已修复为检查恢复结果、失败保留备份；SHA拒绝后的真实回滚已通过，见下文。
- 接续期间未连接生产NAT机；长期、IPv6与破坏性测试仍保留未验证状态。
- 回滚补充首轮：172项Linux测试通过；真实不同SHA候选被拒绝且内层恢复正确，外层仍失败并保留私有备份，主节点未自动恢复。已立即用独立官方核心备份恢复服务；当前SHA正确且active，继续定位，不能将本轮回滚标PASS。

- 回滚最终修复：增加逐步诊断，定位Debian嵌套EXIT回滚中端口helper裸return输出443但返回1；改为显式成功，保留原部署失败状态。前两次失败记录保留，独立安全备份均恢复了服务。
- 最终不同SHA候选真实到达拒绝门禁，部署exit1符合预期；官方核心SHA、配置/env/元数据/密码/链接文件全部不变，主节点自动active，fallback timer已停。Windows主节点curl0、出口正确，doctor0错误0警告，networking与管理timer active，失败unit0。测试VPS入口脚本已同步修复源码。
- 新增8项真实生成函数隔离回归和7项发布检查在Linux通过；旧166项通过证据复用。对应最终提交的全量CI按Actions结果核对，不将本轮定向检查称为重复全量真机验收。

## SOCKS5 独立可选组件原样复制
- 用户明确要求复用成熟实现：从 jieshu `89c55085a57a57fadcf69e6c21a60b4cbf23d16c` Git 原始对象复制 core/installer/traffic/audit 和原审计测试；5文件SHA256及Git Blob一致，3个安装器内置SHA匹配。详见[静态复用记录](docs/SOCKS5_UPSTREAM_REUSE.md)。
- README补齐独立落地机可选安装与管理；四文件同目录使用原安装器本地分支，原远程fallback仍为jieshu，未改实现/依赖/校验。HY2入口不自动安装，SOCKS5仅TCP CONNECT。
- 本次不执行任何SOCKS5功能测试或服务器操作；按相同源码/依赖/条件复用上游已有真机证据，待验收清单不冒充通过。
- 原测试文件保留不执行；CI在导入前排除该文件，仅静态校验SOCKS包，原HY2测试继续保留。后续AI不得通配发现并重跑SOCKS5功能测试。
- 唯一修改仓库仍为hy2jieshu，jieshu全程只读，生产机未连接。
