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
- 最终Windows主节点curl0且出口正确、hy2-abuse443退出0、严格doctor0错误0警告通过；官方2.14.0 amd64 SHA核对后固定。最后提交推送本轮文档并核对其CI；Linux166项已通过。
- VPS测试策略、临时meta及测试监听已清；仅UDP443为HY2监听，guard0pause0ban、portbw空策略；测试WG停用/私有归档，Stats secret删除，生产NAT无残留。
- IPv6因VPS无全局地址/域名无AAAA未测；实际72小时/30天、真实CA续证、核心升级失败回滚、异常断电、生产NAT重启未测。
- IP_LIMIT第二来源为VPS回环；丢配额表测试已用0；未重复portbw算法压测。HY2新NAT安装器修复、WG未来握手时间拒绝仅自动化/正常握手覆盖，未生产安装nat.sh或真机调时。

## 接续
- 先读本文件、最近git提交与本轮报告，再确认机器实际状态；已通过且代码未变的项目不重复测试。
- 保留失败和未测边界；仅把当前实际执行场景记为当前真机通过。重要进展及时提交推送。

## 保存时的补充交接

- 本轮修改及新增文件已做敏感信息排查；不提交原始私有日志、真实凭据或节点链接。
- 额外系统观察：测试 VPS 的 networking.service 因尝试启用不存在的 eth1 而失败；当前 eth0 默认路由、SSH 与 HY2 客户端均正常。未改动或重启网络服务，留待后续单独处理；HY2 严格体检 0 错误不等同于全部操作系统服务健康。
- 按用户额度要求停止扩展工作；长期与未验证项保持上文状态，生产服务器不再执行写操作。
