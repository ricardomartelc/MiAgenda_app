"""Persistencia SQLite y operaciones de respaldo."""
import sqlite3

from src.config import DB_PATH, DEFAULT_CATS

# -------------------------------------------------------------------- base de datos
SCHEMA = """
CREATE TABLE IF NOT EXISTS tareas(id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL,
    fecha TEXT, prioridad TEXT DEFAULT 'Media', hecha INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS notas(id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, texto TEXT);
CREATE TABLE IF NOT EXISTS categorias(id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, color TEXT);
CREATE TABLE IF NOT EXISTS habitos(id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, emoji TEXT DEFAULT '⭐');
CREATE TABLE IF NOT EXISTS habito_log(habito_id INTEGER, fecha TEXT, PRIMARY KEY(habito_id, fecha));
CREATE TABLE IF NOT EXISTS animo(fecha TEXT PRIMARY KEY, valor INTEGER, nota TEXT);
CREATE TABLE IF NOT EXISTS metas(id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL, fecha_limite TEXT);
CREATE TABLE IF NOT EXISTS subtareas(id INTEGER PRIMARY KEY AUTOINCREMENT, meta_id INTEGER,
    titulo TEXT NOT NULL, hecha INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS gastos(id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT,
    cantidad REAL, tipo TEXT DEFAULT 'Gasto', categoria TEXT);
CREATE TABLE IF NOT EXISTS pomodoros(id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, minutos INTEGER);
CREATE TABLE IF NOT EXISTS horario(id INTEGER PRIMARY KEY AUTOINCREMENT, dia INTEGER NOT NULL,
    hora INTEGER NOT NULL, titulo TEXT NOT NULL, detalle TEXT DEFAULT '', color TEXT DEFAULT '#7c3aed',
    UNIQUE(dia, hora));
"""
TABLES = ["tareas", "notas", "categorias", "habitos", "habito_log", "animo", "metas",
          "subtareas", "gastos", "pomodoros", "horario"]
NEW_COLS = {"tareas": [("hora", "TEXT"), ("categoria", "TEXT"), ("recurrencia", "TEXT DEFAULT ''"),
                       ("avisada", "INTEGER DEFAULT 0"), ("generada", "INTEGER DEFAULT 0"),
                       ("hecha_en", "TEXT")]}


class DB:
    def __init__(self):
        self.con = sqlite3.connect(DB_PATH)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        for table, cols in NEW_COLS.items():  # migración de bases de datos antiguas
            have = {r["name"] for r in self.con.execute(f"PRAGMA table_info({table})")}
            for name, typ in cols:
                if name not in have:
                    self.con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
        if not self.con.execute("SELECT 1 FROM categorias LIMIT 1").fetchone():
            self.con.executemany("INSERT INTO categorias(nombre,color) VALUES(?,?)", DEFAULT_CATS)
        self.con.commit()

    def run(self, sql, args=()):
        cur = self.con.execute(sql, args)
        self.con.commit()
        return cur

    def all(self, sql, args=()):
        return self.con.execute(sql, args).fetchall()

    def one(self, sql, args=()):
        r = self.con.execute(sql, args).fetchone()
        return (r[0] or 0) if r else 0

    def export_all(self):
        return {t: [dict(r) for r in self.all(f"SELECT * FROM {t}")] for t in TABLES}

    def import_all(self, data):
        try:
            for t in TABLES:
                self.con.execute(f"DELETE FROM {t}")
                cols = {r["name"] for r in self.con.execute(f"PRAGMA table_info({t})")}
                for row in data.get(t, []):
                    keys = [k for k in row if k in cols]
                    if not keys:
                        continue
                    self.con.execute(
                        f"INSERT OR REPLACE INTO {t}({','.join(keys)}) VALUES({','.join('?' * len(keys))})",
                        [row[k] for k in keys])
            self.con.commit()
        except Exception:
            self.con.rollback()
            raise

    def backup_to(self, path):
        dst = sqlite3.connect(path)
        self.con.backup(dst)
        dst.close()
