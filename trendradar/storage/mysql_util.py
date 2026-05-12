# coding=utf-8
"""MySQL 辅助：执行多语句 DDL（按分号拆分，适用于本仓库 schema 文件）"""


def run_mysql_script(cursor, sql_text: str) -> None:
    buf: list[str] = []
    for line in sql_text.split("\n"):
        s = line.strip()
        if not s or s.startswith("--"):
            continue
        buf.append(line)
        if ";" in line:
            stmt = "\n".join(buf).strip()
            while stmt.endswith(";"):
                stmt = stmt[:-1].strip()
            if stmt:
                cursor.execute(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        while tail.endswith(";"):
            tail = tail[:-1].strip()
        if tail:
            cursor.execute(tail)
