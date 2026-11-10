import re
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)  # timers run on other threads
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS facts(id INTEGER PRIMARY KEY, fact TEXT UNIQUE, ts DEFAULT CURRENT_TIMESTAMP);"
            "CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, role TEXT, content TEXT, ts DEFAULT CURRENT_TIMESTAMP);")

    def add_fact(self, fact: str) -> None:
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO facts(fact) VALUES (?)", (fact.strip(),))

    def facts(self, limit: int = 30) -> list[str]:
        return [r[0] for r in self.db.execute("SELECT fact FROM facts ORDER BY id DESC LIMIT ?", (limit,))]

    def search(self, query: str) -> list[str]:
        words = [w for w in re.findall(r"\w+", query) if len(w) > 2]
        if not words:
            return []
        where = " OR ".join("fact LIKE ?" for _ in words)
        return [r[0] for r in self.db.execute(f"SELECT fact FROM facts WHERE {where}", [f"%{w}%" for w in words])]

    def add_turn(self, role: str, content: str) -> None:
        with self.db:
            self.db.execute("INSERT INTO history(role, content) VALUES (?, ?)", (role, content))

    def recent(self, turns: int) -> list[dict]:
        rows = self.db.execute("SELECT role, content FROM history ORDER BY id DESC LIMIT ?", (turns * 2,)).fetchall()
        return [{"role": r, "content": c} for r, c in reversed(rows)]
