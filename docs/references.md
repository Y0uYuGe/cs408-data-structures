# 参考资料与原创范围

下列为已查阅的一手/原作者资料，访问核对日期2026-10-15。仓库实现、示例、题目和中文解释为原创；没有复制教材整章或历年试题。

1. [Virginia Tech OpenDSA项目主页](https://opendsa.cs.vt.edu/)：可视化数据结构与算法课程体系，作为结构/算法分类与教学推演参考。
2. [OpenDSA独立模块集合](https://opendsa.cs.vt.edu/ODSA/StandaloneModules/20251119180353/html/index.html)：顺序/链式存储、栈队列、二叉树、内部排序与图模块。链接含版本时间路径，若以后迁移可从项目主页导航。
3. [OpenDSA Huffman Coding Trees](https://opendsax.cs.vt.edu/ODSA/Books/Everything/html/Huffman.html)：Huffman贪心合并、带权外部路径长度与前缀编码概念，对应07树和归档功能。
4. [Clifford A. Shaffer原作者《Data Structures and Algorithm Analysis》教材](https://people.cs.vt.edu/shaffer/Book/Java3e20110910.pdf)：算法分析、ADT、树、排序与图的原作者公开教材；教材语言Java，仓库实现独立使用Python/C/C++。
5. [OpenDSA Trees versus Tries](https://opendsax.cs.vt.edu/OpenDSA/Books/Everything/html/TreeTrie.html)：按完整键比较的树与按字符分支Trie的区别，对应06/08章。

这些资源用于验证一般算法原理，不是中国408官方范围证明。未来年度考试科目、大纲和细目需从报考年度官方发布材料核对；仓库不声称已核对某一未来大纲，也不转载未获提供的整套真题。

## 实现与教材模型的区别

Python顺序表用预分配Python列表作为底层槽位，但手写逻辑大小、倍增、插删与检查。HashMap链桶、Stack/Queue、AVL、Trie、MinHeap、KMP、Huffman、八排序和图算法均为仓库代码。JSON、Unicode正则、文件I/O、SHA-256是标准库工具，不伪装为手写实现。邻接表底层采用字典/集合辅助状态；图算法过程独立实现。

教科书堆排序通常原地最大堆；Python版本用最小堆收集输出、逐项push建堆；C++对照为原地最大堆。这种差别已在10章说明，不能套用相同额外空间或建堆代价。
