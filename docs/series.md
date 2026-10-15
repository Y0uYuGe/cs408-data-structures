# 四科如何一起学习

四个仓库独立运行，主系统均使用Python3.11+标准库；数据结构另有C11/C++17对照。建议先完成每科的起步工作流，再按各自的六级路线逐层推进，不要求先读完另一科。

| 科目 | 系统 | 可验证产出 |
| --- | --- | --- |
| [数据结构](https://github.com/Y0uYuGe/cs408-data-structures) | AtlasSearch | 自己的笔记被索引、检索、更新、压缩备份并恢复 |
| [计算机组成原理](https://github.com/Y0uYuGe/cs408-computer-organization) | AtlasMachine | 汇编成真实编码，执行输入统计、递归调用、中断及DMA存盘 |
| [操作系统](https://github.com/Y0uYuGe/cs408-operating-systems) | AtlasOS | 自己的程序经历调度/阻塞/分页，把文件保存并跨进程恢复 |
| [计算机网络](https://github.com/Y0uYuGe/cs408-computer-networks) | AtlasNet | 通过真实TCP与自写可靠UDP传输文件，观察协议及路由 |

## 建议贯穿任务

把各科笔记作为AtlasSearch的输入，把检索结果导出后用AtlasNet传输；在AtlasMachine运行统计程序，读取其RAM/磁盘结果；在AtlasOS写任务完成读写/同步/内存操作。它们不共享内部ABI，不会把教学机器的二进制直接当作另一仓库可执行程序。跨科连接通过明确的文本或文件数据进行。

每完成一章：先手算，再预测程序结果，运行测试对照，解释失败原因，最后闭卷写出同类题的推导。工程结果与考试书面表达需要分别训练。

“从零到满分”是能力训练目标；原创题的诊断分数不预测考研分数。按408通行核心知识建设，报考年度新增删考点仍需核对当年正式大纲。所有模型均在本仓库注明边界，不把用户态模型声称为真实硬件或宿主内核。
