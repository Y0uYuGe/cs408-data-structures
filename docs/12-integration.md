# 12 综合项目：一次更新穿过所有数据结构

级别6。代码主流程`engine.py`，接口`__main__.py:dispatch`，真实工作负载见`tests/test_engine.py`和`tests/test_cli.py`。目标是解释“为什么改一篇文档需要维护多个结构”，并能定位索引不一致。

## 从原文到结果

添加ID=1，标题X，正文`alpha beta beta`。tokenize产生x,alpha,beta,beta；freq[1]是`x:1,alpha:1,beta:2`。postings分别含ID1，每个词每篇文档只插一次，即使beta出现两次。Trie加入x/alpha/beta，AVL加入`(15,1)`，documents保存原文。commit把文档保存到磁盘，下一进程重建相同结构。

另一篇ID2正文`beta`，查询beta得分ID1为2、ID2为1，所以先输出1。如果ID2标题也叫Beta，得分变2，与ID1同分按ID升序。排名测试必须按真实评分规则计算，不能忽略标题。

## 更新是一组配套操作

把ID1正文更新成`gamma`：先取旧freq，分别从x、alpha、beta倒排表删除1；若某词表空，删除HashMap条目并Trie.remove；从sizes删旧键；删除旧freq。再对新标题和正文分词加入新结构，ID保留，最后提交。beta仍有ID2，因此不能整个删词条。更新不是往旧索引上不断叠加新词。

删除ID2还要清理其他文档links中指向2的项，否则显式图含悬空边。文档表删掉记录后，graph只构建仍存活的文档；共享词关系也随词频变化重算。测试在修改后立即check，再用新Engine重启验证，避免只证明一份内存对象状态。

## check核验什么

check重新由原文构造预期“词→唯一有序ID集合”，与实际postings比较；验证AVL BST顺序、高度和平衡；核验尺寸结点数量；比较Trie词汇与postings键；验证payload链接/ID等。它不测相关性好坏、不证明排序所有输入正确，也不替代磁盘校验。故意在某倒排表append999会被检测，这是一个具体可检验的不变量。

## 端到端实验

在干净库index三篇样文，然后search `tree OR graph`；分别使用八排序确认一致。切换linked后重复；add一篇包含仅它独有的词，update去掉该词，确认search与suggest均无旧词；delete并重启check。导出归档到外部文件，另一个空库import，比较原库与恢复库查询ID及排名。

读取所有目录文件后再开始index变更，所以其中一个文件UTF-8解码失败会阻止本轮全部更新。正常写入发生文件系统错误时，CLI进程会报错退出；保存可能已经完成主副本替换，因此不能根据错误码断言“一点都未提交”，应重启check查看revision。这不是数据库级完整事务/WAL系统。

## 系统设计取舍

当前实现把难点保持可见：手写结构能观察每次插删，快照可读，算法可选择，错误有JSON。但它没有并发读优化、磁盘倒排段合并、全文BM25、分片、增量日志、复杂分词。未来可用B+树持久化长度索引或外排构建大倒排表，但要增加真实页管理与测试才能标implemented。

## 故障练习与答案

1. 删除后search崩溃于不存在ID，先查哪？答案postings是否仍含该ID；然后查删除流程是否_unindex。
2. search正常但suggest仍给唯一旧词，先查哪？答案词倒排清空时是否Trie.remove，以及共享前缀剪枝条件。
3. 相同长度两篇仅返回一篇，先查哪？答案AVL键是否用了(length,id)，不能只用length。
4. 两个同时写进程各返回成功但只剩一个新增，先查哪？答案读—改—提交整个区间是否加锁，而不是只在最终write时加锁。
