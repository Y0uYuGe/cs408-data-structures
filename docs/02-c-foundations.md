# 02 C基础：对象、数组、指针与生命周期

级别1。Python便于先构建系统，但408的算法表达常采用C/C++。这里将Python的“引用一个结点”还原为C的地址与指针。对应`c/basics.c`、`cpp/core.cpp:Sequence`、`atlas_search/structures.py:Link`。C代码带断言；是否实际编译以`validation.md`记录为准。

## 从变量到内存

`int x=3; int *p=&x;`创建一个int对象x和一个指针对象p。`&x`取x地址，`*p`访问该地址上的int。执行`*p=7`修改x；执行`p=&y`修改指针本身。变量名只是程序对对象的命名，指针值不是对象的业务值。

`int a[4]={10,20,30,40};`在连续存储区放四个int，下标0至3。`a[i]`等价于`*(a+i)`，前进i个**int对象**，不是i个字节。`a+4`可作为一过尾位置比较，但不可解引用。C不会像本仓库Python顺序表那样自动检查越界；越界产生未定义行为，并不保证立刻报错。

## 用结构体表示链表

`typedef struct Node { int value; struct Node *next; } Node;`把业务值和后继地址组合起来。空链用`NULL`表示。头指针存放第一个结点地址，尾结点的next是NULL。`malloc(sizeof *node)`申请一个结点大小；检查返回是否为NULL，再写字段。`free(node)`结束动态对象生命周期，释放之后访问它是错误。

`push(Node **head,int value)`为何使用二级指针？调用者的头指针本身也是一个对象。把`&head`传入，函数才能修改调用者保存的首结点地址；单传`Node *head`只会得到指针值的副本。

## 删除过程逐步推演

链为`head→3→2→1→NULL`，要删3：保存`victim=*cursor`，把`*cursor`改成`victim->next`，然后free(victim)。删中间2时，cursor指向“前一个结点next字段”，同样三行即可；这就是指向指针的技巧。每一轮必须先保留后继再释放当前结点，释放后不可再读取victim->next。

本仓库C示例依次删头3、尾1、最后单结点2，并断言head最终为NULL。Python版LinkedList还显式维护tail与size，因此删除尾结点要同步改tail，删除最后结点要让head和tail同时为空。

## C++所有权对照

`Sequence<T>`构造时`new T[4]`，析构时`delete[]`，扩容时先分配新块、搬移、再释放旧块。示例禁用复制，避免两个Sequence持有同一个地址并分别释放。完整生产容器还需处理移动、异常安全和迭代器失效，这里只保留教学核心。不要把示例当成std::vector的完整替代品。

编译示例：`gcc -std=c11 -Wall -Wextra -pedantic c/basics.c -o c-basics`；`g++ -std=c++17 -Wall -Wextra -pedantic cpp/core.cpp -o atlas-core`。Linux运行`./atlas-core`，Windows运行`./atlas-core.exe`。Python系统不依赖编译器。

## 常见错误与练习

错误：用`sizeof(pointer)`当数组总长度；malloc后忘记初始化next；释放两次；返回局部栈变量地址；只改函数内head副本；`new[]`与`free`混用。

练习1：已有p指向结点B，如何在B后插入X？答案：先`X->next=p->next`，再`p->next=X`，反过来会丢失原后继。

练习2：`int a[3]; int *p=a+3;`合法吗？答案：建立一过尾指针合法，`*p=1`非法。练习3：`free(p); p=NULL;`能否修复另一指针q的悬空？答案：不能，q仍保存已释放地址，必须从所有权设计上避免继续访问。
