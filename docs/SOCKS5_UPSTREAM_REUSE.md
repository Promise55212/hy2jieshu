# SOCKS5 原样复用记录（2026-11-15）

来源为只读 `liucong552-art/jieshu` 的提交
[`89c55085a57a57fadcf69e6c21a60b4cbf23d16c`](https://github.com/liucong552-art/jieshu/commit/89c55085a57a57fadcf69e6c21a60b4cbf23d16c)。复制时已核对远程 main 与该快照相同。直接读取 Git 原始对象，避免 Windows 工作树 CRLF 转换改变发布字节；实现、安装器和原测试均未修改。

| 文件 | SHA256 |
|---|---|
| `socks5.py` | `4c6d97e82749973d17274d96dc3f3cf828ca357638fcc6019c487ba3f49a3dcf` |
| `socks5-install.sh` | `b335592be4ead45d10fffd2a5dc4a6ffeef9a5f50313cab40f55a651b855bf90` |
| `socks5-traffic.py` | `134bcd2a2ee8947bcad3bad09c6f0d50ea5474249701758c514a2294274deb23` |
| `socks5-audit.py` | `3c6e1bb357959e12d04c9adf2ba0a99f51ca349c4b812f8b6981259843acf7c8` |
| `tests/test_socks5_access_audit.py` | `bb6f6d331c2770aaeaa30ecb2f5d8778cb29da37d2c90196bb4d76cfa1f5b980` |

表中哈希记录原始上游文件，见 [SHA / Git Blob 清单](../tests/SOCKS5_UPSTREAM_MANIFEST.json)。仓库迁移到 Promise55212 后，安装器和相应测试中的下载地址改为同账户的 jieshu。完整性检查先还原这一个地址，再核对原始哈希。安装器内置的 core、traffic、audit 三个 SHA 与下载文件一致。

## 配套条件

- 独立落地机、root、Debian/Ubuntu apt、systemd、IPv4 公网物理出口；不在 HY2 入口机自动安装，不修改现有生产落地机。
- Python 3 标准库，无 pip 依赖；访问审计需要 journald/journalctl 及 `Asia/Shanghai` 时区数据。日志查询窗口不等于系统实际保留时长。
- 依赖命令为 `3proxy python3 nft ip ss timeout systemctl flock`；下载/依赖引导另需 curl、CA 和 gnupg。原安装器包清单为 `ca-certificates curl gnupg python3 nftables iproute2 util-linux coreutils procps`。
- 3proxy 优先使用已安装程序或发行版软件包，否则原安装器使用 `https://3proxy.org/repo/deb`，校验签名公钥指纹 `FC12214499FCC7BA1CFF6CDC0312384E3A73940B`。
- 四文件同目录下载时，安装器读取本地配套模块。缺少任一模块时从 `Promise55212/jieshu` 下载，默认使用 `main`，也可通过 `S5_SOURCE_REF` 指定 `feature/socks5-access-audit`。两个分支的三个配套文件都通过了安装器的 SHA256 校验。
- SOCKS5 为 IPv4 TCP CONNECT，原实现拒绝 UDP ASSOCIATE/BIND；状态、锁、规则和服务使用独立 `socks5-manager` / `s5m_*` 命名空间。portbw 是独立可选组件，不是安装硬依赖；SOCKS5 账号生命周期不自动改动其策略。
- 可选 Cloudflare DDNS 需另外配置 zone、record 和 root 私有 Token 文件。本次不配置、不复制任何真实 Token 或用户数据。

## 验收归属与 CI

用户明确确认该成熟组件已在 jieshu 完成真机验收；源码、依赖和适用条件相同时直接复用其既有结果。参考 [上游 README](https://github.com/liucong552-art/jieshu/blob/89c55085a57a57fadcf69e6c21a60b4cbf23d16c/README.md#socks5) 和[历史验收记录](https://github.com/liucong552-art/jieshu/blob/89c55085a57a57fadcf69e6c21a60b4cbf23d16c/tests/SOCKS5_AUDIT_REAL_MACHINE_ACCEPTANCE.md)中明确有证据的范围；其中待验收清单仍为待验收，不扩大为所有系统和部署方式均通过。

本次仅静态核对文件 SHA / Git Blob、安装器固定 SHA、依赖、下载来源及文档引用。没有执行 SOCKS5 安装器、管理命令、功能单测或客户端测试，没有连接任何服务器。

原功能测试文件保留在原路径，保持其 ROOT 引用有效。CI 先运行 `scripts/check_socks5_bundle.py`，再由 `tests/run_hy2_checks.py` 在调用测试发现器前排除该 SOCKS5 文件，既不导入也不运行它；原 HY2 测试覆盖保持。不要直接使用通配 discovery 重跑复制的 SOCKS5 功能测试；这不是本次复用任务的验收要求。

安装与管理入口见 [README 6.5](../README.md#socks5)。
