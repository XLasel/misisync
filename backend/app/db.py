import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS groups (name TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS lessons (
    id TEXT PRIMARY KEY,
    group_name TEXT NOT NULL REFERENCES groups(name),
    weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
    start_time TEXT NOT NULL, end_time TEXT NOT NULL,
    subject TEXT NOT NULL CHECK(length(subject)>0),
    lesson_type TEXT NOT NULL, teacher TEXT NOT NULL, room TEXT NOT NULL,
    subgroup TEXT NOT NULL, week_pattern TEXT NOT NULL CHECK(week_pattern IN ('all','odd','even')),
    notes TEXT NOT NULL, raw_text TEXT NOT NULL,
    source_url TEXT NOT NULL, source_sheet TEXT NOT NULL, source_cell TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lessons_group_day_time ON lessons(group_name, weekday, start_time);
CREATE TABLE IF NOT EXISTS sync_state (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
    last_success TEXT, last_attempt TEXT, last_error TEXT,
    source_url TEXT NOT NULL DEFAULT '', warnings TEXT NOT NULL DEFAULT '[]'
);
INSERT OR IGNORE INTO sync_state(singleton) VALUES(1);
PRAGMA user_version=1;
"""


class Database:
    def __init__(self, path):
        self.path = path

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def initialize(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript(SCHEMA)

    def replace(self, lessons, groups, timestamp, source_url, warnings):
        if not lessons or not groups:
            raise ValueError('Refusing empty snapshot')
        records = {lesson.record()['id']: lesson.record() for lesson in lessons}
        columns = list(next(iter(records.values())))
        # Parsing and network I/O have already finished. Readers see the previous
        # snapshot throughout this transaction, then the entire new snapshot.
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM lessons')
            db.execute('DELETE FROM groups')
            db.executemany('INSERT INTO groups(name) VALUES(?)', [(g,) for g in sorted(groups)])
            db.executemany(f"INSERT INTO lessons({','.join(columns)}) VALUES({','.join('?' for _ in columns)})", [tuple(r[c] for c in columns) for r in records.values()])
            db.execute('UPDATE sync_state SET last_success=?, last_attempt=?, last_error=NULL, source_url=?, warnings=? WHERE singleton=1', (timestamp, timestamp, source_url, json.dumps(warnings, ensure_ascii=False)))

    def failure(self, timestamp, message):
        with self.connect() as db:
            db.execute('UPDATE sync_state SET last_attempt=?, last_error=? WHERE singleton=1', (timestamp, message))

    def status(self):
        with self.connect() as db:
            db.execute('BEGIN')
            state = dict(db.execute('SELECT * FROM sync_state WHERE singleton=1').fetchone())
            state.pop('singleton')
            state['warnings'] = json.loads(state['warnings'])
            state['group_count'] = db.execute('SELECT COUNT(*) FROM groups').fetchone()[0]
            state['lesson_count'] = db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0]
            return state

    def groups(self):
        with self.connect() as db:
            return [r[0] for r in db.execute('SELECT name FROM groups ORDER BY name')]

    def schedule(self, group, weekday=None):
        with self.connect() as db:
            query = 'SELECT * FROM lessons WHERE group_name=?'
            params = [group]
            if weekday is not None:
                query += ' AND weekday=?'
                params.append(weekday)
            return [dict(r) for r in db.execute(query + ' ORDER BY weekday,start_time,subject,subgroup,week_pattern', params)]
