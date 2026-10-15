# 01 环境、运行与第一份可检索笔记

级别1。目标是认识“源文件—解释执行—进程—持久化文件”的区别，并能独立重现一个成功查询。代码入口为`atlas_search/__main__.py:main`，持久化入口为`atlas_search/storage.py:load`，跨进程证据在`tests/test_cli.py`。

## 先建立可复现环境

安装Python3.11以上，打开本仓库目录的终端，执行`python --version`。不需要安装IDE或任何第三方Python包。执行`python -m atlas_search --help`，`-m`表示把包当模块运行，Python会寻找该包的`__main__.py`。如果提示找不到模块，先检查当前目录是否含`atlas_search`目录。

```console
python -m atlas_search --db .atlas init
python -m atlas_search --db .atlas add --title "第一篇" --text "tree 数据结构"
python -m atlas_search --db .atlas search tree
python -m atlas_search --db .atlas list
```

第一条创建空库，第二条返回`{"id":1}`，第三条返回文档结果，第四条显示保存的原文。每条命令都是新进程：上一个Python进程退出后，内存中的结构已经消失；新进程重新读快照并构建索引。所以“第二次还能找到”证明跨进程持久化，而同一对象连续调用并不能单独证明它。

## 区分三个位置

仓库目录放源代码与测试；源文档目录放笔记；`--db`指定数据库目录。相对路径以当前终端目录为基准。你可以执行`index examples/corpus`导入仓库附带的三篇笔记。系统只读`.txt`和`.md`且使用UTF-8，二进制文件和其他后缀忽略。源目录中的文件更新后再次index会按绝对路径更新旧ID；移走源文件不会自动删除索引。

## 读懂失败

`python -m atlas_search --db .atlas delete 999`返回错误JSON和退出码2。终端里的一长串异常不等于算法复杂，常见原因是路径错误、文件编码错误、使用不存在的ID或表达式括号不匹配。参数`--db`必须放在子命令前。Windows文件路径含空格时加双引号；查询内部需要双引号短语时用外层单引号，例如`search '"数据结构"'`。

Python以Unicode字符处理正文；长度是字符数而不是UTF-8字节数。`len('数据')=2`，UTF-8编码后6字节。之后的AVL长度范围与Huffman字节压缩正好能比较这两个概念。

## 测试是可复现的实验

执行`python -m unittest discover -s tests -v`。每个测试在临时目录建库并清理，避免污染你的笔记。测试失败时先读最后的预期/实际差异，再追到对应模块。只见`OK`意味着这些用例成立，不能推广成所有规模、断电和并发情形都正确。

练习1：关闭终端后重新打开，在仓库目录执行同样的search会发生什么？答案：只要`--db`仍指向原目录且快照有效，文档仍能找到。

练习2：正文`数据`的range应该查`2 2`还是`6 6`？答案：`2 2`。范围索引按Python字符数；压缩器接收UTF-8字节。

练习3：把所有原始文档移走后执行index，旧记录是否消失？答案：不会。需要显式delete；这是防止误删学习资料的明确接口语义。
