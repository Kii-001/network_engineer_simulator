"""Penyimpanan progres pemain dan pengaturan dengan SQLite."""
import json
import sqlite3
from pathlib import Path

import config


class SaveManager:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else config.DB_PATH
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        self._ensure_defaults()

    def _create_tables(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    name TEXT NOT NULL DEFAULT 'Technician',
                    rank TEXT NOT NULL DEFAULT 'Junior Network Technician',
                    xp INTEGER NOT NULL DEFAULT 0,
                    coins INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS mission_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level_id INTEGER NOT NULL,
                    stars INTEGER NOT NULL DEFAULT 0,
                    score INTEGER NOT NULL DEFAULT 0,
                    seconds REAL NOT NULL DEFAULT 0,
                    completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS topologies (
                    slot TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                """
            )

    def _ensure_defaults(self) -> None:
        with self._conn:
            for key, value in config.DEFAULT_SETTINGS.items():
                self._conn.execute(
                    "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (key, value)
                )
            self._conn.execute("INSERT OR IGNORE INTO profile(id) VALUES (1)")

    # --- settings ---
    def get_setting(self, key: str) -> str:
        row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise KeyError(f"Pengaturan tidak dikenal: {key}")
        return row["value"]

    def get_bool(self, key: str) -> bool:
        return self.get_setting(key) == "1"

    def set_setting(self, key: str, value: str) -> None:
        if key not in config.DEFAULT_SETTINGS:
            raise KeyError(f"Pengaturan tidak dikenal: {key}")
        with self._conn:
            self._conn.execute("UPDATE settings SET value = ? WHERE key = ?", (str(value), key))

    def toggle_bool(self, key: str) -> bool:
        new_value = not self.get_bool(key)
        self.set_setting(key, "1" if new_value else "0")
        return new_value

    # --- profile ---
    def get_profile(self) -> dict:
        return dict(self._conn.execute("SELECT * FROM profile WHERE id = 1").fetchone())

    def set_player_name(self, name: str) -> str:
        name = " ".join(name.split())[:20]
        if not name:
            raise ValueError("Nama pemain tidak boleh kosong.")
        with self._conn:
            self._conn.execute("UPDATE profile SET name = ? WHERE id = 1", (name,))
        return name

    def add_mission_result(self, level_id: int, stars: int, score: int, seconds: float) -> None:
        if not 0 <= stars <= 3:
            raise ValueError("Stars harus 0-3.")
        with self._conn:
            self._conn.execute(
                "INSERT INTO mission_results(level_id, stars, score, seconds) VALUES (?,?,?,?)",
                (level_id, stars, score, seconds),
            )

    def add_rewards(self, xp: int, coins: int) -> dict:
        with self._conn:
            self._conn.execute("UPDATE profile SET xp = xp + ?, coins = coins + ? WHERE id = 1", (xp, coins))
            row = self._conn.execute("SELECT xp FROM profile WHERE id = 1").fetchone()
            cur_xp = row["xp"]
            rank = "Junior Network Technician"
            if cur_xp >= 7000:
                rank = "Principal Network Architect"
            elif cur_xp >= 3500:
                rank = "Senior Network Engineer"
            elif cur_xp >= 1500:
                rank = "Network Administrator"
            elif cur_xp >= 500:
                rank = "Network Technician"
            self._conn.execute("UPDATE profile SET rank = ? WHERE id = 1", (rank,))
        return self.get_profile()

    def get_mission_stars_map(self) -> dict[int, int]:
        rows = self._conn.execute("SELECT level_id, MAX(stars) as best_stars FROM mission_results GROUP BY level_id").fetchall()
        return {r["level_id"]: r["best_stars"] for r in rows}

    def get_mission_results(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM mission_results ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    # --- topologi ---
    def save_topology(self, slot: str, data: dict) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO topologies(slot, data, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(slot) DO UPDATE SET data = excluded.data, updated_at = CURRENT_TIMESTAMP",
                (slot, json.dumps(data)),
            )

    def load_topology(self, slot: str) -> dict | None:
        row = self._conn.execute("SELECT data FROM topologies WHERE slot = ?", (slot,)).fetchone()
        if row is None:
            return None
        try:
            return json.loads(row["data"])
        except json.JSONDecodeError:
            return None

    def close(self) -> None:
        self._conn.close()
