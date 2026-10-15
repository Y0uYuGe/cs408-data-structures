# 11 持久化、原子替换与恢复

级别6。代码`storage.py`、`engine.py:commit/rebuild/export_archive/import_archive`；证据在`test_snapshot_corruption_recovery_and_repair`、`test_cli_corruption_recovers_latest_documents`与锁测试。

## 保存原始数据，重建派生结构

快照payload保存schema、revision、next_id、倒排后端、文档原文/标题/来源/links。词频、倒排、AVL、Trie与共享词图都从原始文档重建。这样恢复时不需要相信已损坏或过期的派生索引；代价是启动O(全库内容)量级，并且每次写入序列化全库，适合学习笔记规模。

包裹层为payload和其规范JSON字节的SHA-256。规范化用键排序和固定分隔符，不能依赖人编辑缩进后的原始字节；verify重算相同规范表示比较checksum，并核验schema、唯一ID、next_id边界、字符串字段、合法链接等语义。checksum匹配只证明数据未偶然改变，不证明谁签名或数据可信。

## 提交流程

commit增加revision，写`snapshot.json.tmp`，flush并fsync，然后os.replace原子替换主文件；再同样更新`snapshot.backup.json`。POSIX额外fsync父目录；Windows没有标准库可移植目录fsync，这里不能承诺断电绝对耐久。

一份文件的replace通常保证读者看到旧完整文件或新完整文件。两份副本并非一个整体原子事务：若主副本已更新、备份尚未更新就进程崩溃，重启选revision更高的主副本；若主损坏而备份还旧，可能退回旧一版。两份均写完后，一份损坏可恢复最新文档。临时文件不是提交证据，启动忽略它，不尝试“猜测”未提交内容。

## 启动与repair

load分别读取两份，校验有效性，在有效候选中选revision最高，平手优先主副本。主坏备份好时Engine.recovered=True，search仍可执行；check显示`recovered_from_backup:true`。`repair`基于已校验的有效文档再提交，把主与备份写回完整快照。双副本均坏则报错并保留损坏文件，不静默初始化空库；用户可从Huffman外部归档或源目录恢复。

## 多进程锁

CLI在读取与操作前用O_EXCL创建writer.lock，所有CLI操作共用排他锁，防止两个写进程从相同旧快照分别提交导致覆盖。锁保存PID，持有进程不存在时可自动回收；活进程持有时最多等待5秒再报busy。Windows通过系统进程API检查，POSIX用kill(pid,0)。PID复用、网络盘锁语义、断电留下未写完锁文件等情形没有完整解决；不明确的空/坏锁不自动删除，报错后需确认无相关进程才手动处理。

Python直接调用Engine不会自动锁。嵌入程序应将“创建Engine、读取、修改、提交”整个过程放进`with database_lock(path):`，避免长期缓存旧Engine再覆盖更新。CLI已经这样做。

## 压缩归档不是快照副本

export将payload编码为UTF-8字节，使用手写Huffman频率树与位打包，再保存原始字节checksum。import限制解压最多64MiB，验证位数、频数、checksum和payload，再替换库；非空库需--replace，避免无意覆盖。Huffman本身不是加密，小文档归档可能更大，完整外部备份应该放到另一个目录或磁盘。

## 练习与答案

1. 主revision5、备份revision4且都有效，选哪份？答案主5。2. 主5损坏、备份4有效能否保证不丢第五次更新？答案不能，只能恢复4；双副本写入之间有窗口。3. 两份都坏能否把空结果当正常？答案不能，必须报错。4. 文件校验有效但doc链接999不存在？答案语义验证也必须拒绝，checksum不能替代不变量。
