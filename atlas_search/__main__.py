"""Run `python -m atlas_search --help` for the complete public interface."""
import argparse
import json
import sys
from pathlib import Path
from .engine import Engine, tokenize
from .storage import database_lock
from .algorithms import SORTS
from .assessment import questions, assess


def parser():
    p = argparse.ArgumentParser(description="AtlasSearch：408数据结构驱动的本地文档检索")
    p.add_argument("--db", default=".atlas", help="数据库目录（放在子命令前）")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="初始化数据库或切换真实倒排表实现")
    init.add_argument("--posting", choices=("array", "linked"), default="array")
    add = sub.add_parser("add", help="添加UTF-8文本")
    add.add_argument("--title", required=True)
    content = add.add_mutually_exclusive_group(required=True)
    content.add_argument("--text"); content.add_argument("--file")
    add.add_argument("--links", type=int, nargs="*", default=[])
    update = sub.add_parser("update", help="更新文档并维护所有索引")
    update.add_argument("id", type=int); update.add_argument("--title")
    content = update.add_mutually_exclusive_group()
    content.add_argument("--text"); content.add_argument("--file")
    update.add_argument("--links", type=int, nargs="*")
    delete = sub.add_parser("delete"); delete.add_argument("id", type=int)
    index = sub.add_parser("index", help="递归upsert目录中的UTF-8 txt/md")
    index.add_argument("directory")
    search = sub.add_parser("search", help="布尔查询，大写AND/OR/NOT，支持双引号短语")
    search.add_argument("expression"); search.add_argument("--limit", type=int, default=10)
    search.add_argument("--sort", choices=SORTS, default="heap")
    suggest = sub.add_parser("suggest"); suggest.add_argument("prefix"); suggest.add_argument("--limit", type=int, default=20)
    ranges = sub.add_parser("range", help="AVL正文字符数闭区间查询")
    ranges.add_argument("minimum", type=int); ranges.add_argument("maximum", type=int)
    show = sub.add_parser("show"); show.add_argument("id", type=int)
    show.add_argument("--lookup", choices=("hash", "binary"), default="hash")
    sub.add_parser("list")
    path = sub.add_parser("path", help="共享词关系路径；--directed使用显式引用图")
    path.add_argument("source", type=int); path.add_argument("target", type=int)
    path.add_argument("--algorithm", choices=("bfs", "dijkstra"), default="bfs")
    path.add_argument("--directed", action="store_true")
    graph = sub.add_parser("graph", help="在真实文档图上选择图算法")
    graph.add_argument("algorithm", choices=("dfs", "floyd", "prim", "kruskal", "topological", "critical"))
    graph.add_argument("--source", type=int); graph.add_argument("--directed", action="store_true")
    for name in ("export", "import"):
        archive = sub.add_parser(name)
        archive.add_argument("file")
        if name == "import":
            archive.add_argument("--replace", action="store_true")
    sub.add_parser("check", help="核验内存索引、AVL和文档不变量")
    sub.add_parser("repair", help="将已验证副本重写为两份有效快照")
    tokens = sub.add_parser("tokenize"); tokens.add_argument("text")
    practice = sub.add_parser("practice", help="输出原创题；--reveal显示答案与推演")
    practice.add_argument("--level", type=int, choices=range(1, 7)); practice.add_argument("--reveal", action="store_true")
    grade = sub.add_parser("assess", help='批改JSON答案，例如 {"Q01":"B"}')
    grade.add_argument("--answers", required=True); grade.add_argument("--level", type=int, choices=range(1, 7))
    return p


def dispatch(args):
    if args.command == "tokenize":
        return tokenize(args.text)
    if args.command == "practice":
        return [q if args.reveal else {k: v for k, v in q.items() if k not in ("answers", "explanation")} for q in questions(args.level)]
    if args.command == "assess":
        answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
        if not isinstance(answers, dict):
            raise ValueError("answers must be a JSON object")
        return assess(answers, args.level)
    with database_lock(args.db):
        engine = Engine(args.db)
        cmd = args.command
        if cmd == "init":
            engine.posting_backend = args.posting
            engine.rebuild(); engine.commit()
            return engine.check()
        if cmd in ("add", "update"):
            text = Path(args.file).read_text(encoding="utf-8") if args.file else args.text
            if cmd == "add":
                return {"id": engine.add(args.title, text, str(Path(args.file).resolve()) if args.file else "", args.links)}
            engine.update(args.id, args.title, text, args.links)
            return {"updated": args.id}
        if cmd == "delete":
            engine.delete(args.id); return {"deleted": args.id}
        if cmd == "index":
            return engine.index_directory(args.directory)
        if cmd == "search":
            return engine.search(args.expression, args.limit, args.sort)
        if cmd == "suggest":
            if args.limit < 0:
                raise ValueError("limit must be nonnegative")
            return engine.trie.prefix(args.prefix.lower(), args.limit)
        if cmd == "range":
            return engine.range(args.minimum, args.maximum)
        if cmd == "show":
            result = engine.locate_id(args.id) if args.lookup == "binary" else engine.documents.get(args.id)
            if result is None:
                raise KeyError(args.id)
            return result
        if cmd == "list":
            return engine.payload()["documents"]
        if cmd == "path":
            return engine.graph(args.directed).path(args.source, args.target, args.algorithm)
        if cmd == "graph":
            graph = engine.graph(args.directed)
            if args.algorithm == "dfs":
                if args.source is None:
                    raise ValueError("dfs requires --source")
                return graph.dfs(args.source)
            if args.algorithm == "floyd":
                return {a: {b: None if distance == float("inf") else distance for b, distance in rows.items()} for a, rows in graph.floyd().items()}
            if args.algorithm in ("prim", "kruskal"):
                return graph.spanning_forest(args.algorithm)
            if args.algorithm == "topological":
                return graph.topological()
            return graph.critical_path()
        if cmd == "export":
            return engine.export_archive(args.file)
        if cmd == "import":
            engine.import_archive(args.file, args.replace); return engine.check()
        if cmd == "repair":
            engine.commit(); return engine.check()
        return engine.check()


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = dispatch(args)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, KeyError, IndexError, TypeError, AttributeError, RuntimeError, OSError, AssertionError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
