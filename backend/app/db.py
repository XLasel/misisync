import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .catalog import education_level, subgroup_ids

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
            columns = {row['name'] for row in db.execute('PRAGMA table_info(groups)')}
            if 'institutes' not in columns:
                db.execute("ALTER TABLE groups ADD COLUMN institutes TEXT NOT NULL DEFAULT '[]'")
            if 'education_level' not in columns:
                db.execute("ALTER TABLE groups ADD COLUMN education_level TEXT NOT NULL DEFAULT ''")
                db.executemany('UPDATE groups SET education_level=? WHERE name=?',
                               [(education_level(row[0]), row[0]) for row in db.execute('SELECT name FROM groups').fetchall()])
            db.execute('PRAGMA user_version=2')

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
            db.executemany('INSERT INTO groups(name,institutes,education_level) VALUES(?,?,?)',
                           [(g, json.dumps(sorted(groups[g]) if isinstance(groups, dict) else [], ensure_ascii=False), education_level(g)) for g in sorted(groups)])
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

    def catalog(self):
        with self.connect() as db:
            return [dict(name=row['name'], institutes=json.loads(row['institutes']), education_level=row['education_level'])
                    for row in db.execute('SELECT name,institutes,education_level FROM groups ORDER BY name')]

    def schedule(self, group, weekday=None, subgroup=None):
        with self.connect() as db:
            query = 'SELECT * FROM lessons WHERE group_name=?'
            params = [group]
            if weekday is not None:
                query += ' AND weekday=?'
                params.append(weekday)
            result = []
            for row in db.execute(query + ' ORDER BY weekday,start_time,subject,subgroup,week_pattern', params):
                item = dict(row)
                item['subgroup_ids'] = subgroup_ids(item['subgroup'])
                if subgroup is None or not item['subgroup_ids'] or subgroup in item['subgroup_ids']:
                    result.append(item)
            return result
