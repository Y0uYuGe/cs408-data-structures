# 408 数据结构：用 AtlasSearch 从零建立完整知识体系

本仓库围绕一个真实可运行的系统学习：**AtlasSearch 本地文档检索引擎**。你把自己的 UTF-8 学习笔记放进目录，就能索引、布尔检索、短语匹配、联想、范围查找、文档关系寻路、压缩备份与恢复。每类核心结构都有系统中的职责，八种排序和两种倒排表都可以在真实工作负载上切换。

课程面向“从零开始、以408高分直至满分为训练目标”的学习者；它提供实现、推演、原创题和诊断，但不能保证考试分数，也不把这套小型引擎称为商用搜索引擎。内容依据408通行数据结构核心范围组织，**没有逐项核对2027等未来年份最新考试大纲**。正式备考请用报考年度官方大纲核对范围，并结合限时整卷与人工审阅。

## 十分钟运行

需要 Python **3.11 或更新版本**，运行和测试均只依赖标准库。Windows PowerShell、macOS/Linux终端均可在本目录执行：

```console
python --version
python -m atlas_search --db .atlas init
python -m atlas_search --db .atlas index examples/corpus
python -m atlas_search --db .atlas search "tree AND NOT graph"
python -m atlas_search --db .atlas search '"数据结构"'
python -m atlas_search --db .atlas suggest tr
python -m atlas_search --db .atlas range 0 200
python -m atlas_search --db .atlas check
python -m unittest discover -s tests -v
```

Windows若命令输出中文编码异常，可在当前终端设置 `$env:PYTHONIOENCODING='utf-8'`；源文档本身必须保存为UTF-8。命令返回JSON；退出码0为成功，2为参数或操作错误。`--db`放在子命令前，每次启动都会恢复相同目录的快照。无需安装依赖、账户、API密钥或网络。可选 `python -m pip install -e .` 安装 `atlas-search` 入口；这一步可能从网络安装构建工具，直接运行模块不需要它。

## 它具体做什么

|功能|真实调用的结构/算法|
|---|---|
|中英分词、添加/更新/删除、目录upsert|动态顺序表、拉链散列、顺序/链式倒排表|
|AND / OR / NOT / 括号 / 隐式AND|栈、中缀转后缀、双指针集合合并|
|双引号短语查找|手写KMP与前缀表|
|得分排名、八种排序选择|最小堆及插入/希尔/冒泡/快速/选择/堆/归并/基数排序|
|正文字符数闭区间查询|维护`(长度, 文档ID)`的AVL，含更新和删除平衡|
|词汇前缀联想|Trie和深度优先栈|
|文档共享词关系与显式引用|BFS、DFS、Dijkstra、Floyd、Prim、Kruskal、并查集、拓扑、关键路径|
|压缩导出/导入|Huffman树、最小堆、位打包、SHA-256校验|
|跨进程保存与损坏恢复|校验双快照、原子替换、排他进程锁、启动重建索引|

核心在 [atlas_search](atlas_search)；[C基础示例](c/basics.c) 与 [C++17核心对照](cpp/core.cpp)帮助你转回考试常见语言。C/C++并非主系统的依赖。

## 六级学习路线

|级别|学习内容|过关产出|
|---|---|---|
|1 起步|环境、C对象/指针、ADT、复杂度|运行系统，画内存图，完成Q01–Q08|
|2 线性组织|顺序表/链表、栈/队列、布尔解析|手推插删、后缀表达式和倒排交集，Q09–Q16|
|3 字符与树|字符串/KMP、Trie、二叉树/AVL、Huffman|画失配回退、四种旋转和编码树，Q17–Q24|
|4 查找|顺序/折半、ASL、散列、平衡树、B/B+树理论|解释查找代价与范围边界，Q25–Q32|
|5 图|表示、遍历、最短路、生成树、拓扑/AOE|比较文档关系图不同语义，Q33–Q40|
|6 综合|八排序、外排理论、持久化、不变量、限时迁移|完成备份恢复与故障定位，Q41–Q48|

从 [课程导航](docs/00-roadmap.md) 按顺序开始。共13个实质章节，每章包含代码定位、逐步推演、常见错误、习题与答案。[topics.json](topics.json)把主要知识点逐项映射到代码、课程和测试；[覆盖说明](docs/coverage.md)明确哪些仅作理论训练。

## 常用操作

```console
python -m atlas_search --db .atlas add --title "我的AVL笔记" --text "AVL tree 数据结构"
python -m atlas_search --db .atlas update 4 --text "balanced tree"
python -m atlas_search --db .atlas show 1 --lookup binary
python -m atlas_search --db .atlas search "tree OR graph" --sort radix --limit 20
python -m atlas_search --db .atlas init --posting linked
python -m atlas_search --db .atlas path 1 2 --algorithm dijkstra
python -m atlas_search --db .atlas graph kruskal
python -m atlas_search --db .atlas export backup.atlas.json
python -m atlas_search --db restored import backup.atlas.json
python -m atlas_search --db .atlas delete 4
python -m atlas_search --db .atlas repair
python -m atlas_search --help
```

上例`4`假定你在干净库索引3篇样文后添加了一篇；实际使用应查看`add`返回ID。`init --posting linked`会保留文档、重建为另一种真实倒排表。`index`更新相同绝对路径的文档，不自动删除已从源目录移走的文件。`import`往非空库恢复需要`--replace`，会替换该库；先保留外部备份。

评分为标题与正文中查询词出现次数之和，同分按ID升序；NOT项也纳入评分词表，布尔成员资格先独立决定。中文采用单字与相邻双字切分，多token普通操作数要求全部出现，**双引号才要求原文连续**。英文不做词干还原，`tree`与`trees`不同。排序/分词/图边权都是可解释的教学规则。

## 原创诊断

```console
python -m atlas_search practice --level 1
python -m atlas_search practice --level 1 --reveal
python -m atlas_search assess --answers examples/answers.example.json
```

将答案模板复制成自己的文件填写，再提交批改。48道题均为本仓库原创，不复制历年真题。选择题填选项字母，数值题填数值，序列题按题目用逗号；空白算未答。诊断给出基础重建/专项补弱/综合迁移/高分巩固分层、错题解释及复习章节。它只检查这组题，不评价主观算法题书写质量。

## 验证与边界

测试包含真实独立进程调用所有公共子命令、跨进程增删改查、重启、删除后索引清理、快照损坏恢复、双副本损坏拒绝、UTF-8文件错误、锁排他、随机AVL不变量、全八排序及Huffman边界。CI配置在Linux与Windows的Python3.11/3.13上运行，并另在Linux编译C/C++；**配置不等于已经在这些环境运行成功**。本机实测记录见[验证说明](docs/validation.md)。

适合几百/几千篇学习笔记。每次启动重建内存索引，提交整库快照，查询图构建为两两比较；没有增量磁盘倒排、BM25、并发读优化、网页抓取、中文词典、B+树或外排实现。仅支持本机单机文件系统，网络盘/多机并发和真实断电耐久性未验证。SHA-256用于检错，不提供加密或来源认证。其他理论范围、恢复局限及后续训练见课程。

## 参考与许可

算法讲解参考Virginia Tech的OpenDSA和原作者教材；精确链接与参考关系见[references.md](docs/references.md)。代码、文档与题目为本仓库原创，MIT许可，见[LICENSE](LICENSE)。

[四科组合学习与贯穿任务](docs/series.md)
