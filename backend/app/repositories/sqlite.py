"""SQLite adapter. A snapshot and its metadata are committed in one transaction."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from ..domain import Catalog, Coverage, Group, Lesson, Schedule, Snapshot, SourceInfo, Status, Window

SCHEMA_VERSION = 3
SCHEMA = '''
CREATE TABLE IF NOT EXISTS groups (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lessons (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL REFERENCES groups(id),
    date TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_group_date ON lessons(group_id, date);
CREATE TABLE IF NOT EXISTS sync_state (
    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
    revision TEXT, source TEXT, coverage TEXT,
    last_success TEXT, last_attempt TEXT, last_error TEXT,
    warnings TEXT NOT NULL DEFAULT '[]'
);
INSERT OR IGNORE INTO sync_state(singleton) VALUES(1);
'''


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
            version = db.execute('PRAGMA user_version').fetchone()[0]
            tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if version != SCHEMA_VERSION and tables:
                raise ValueError('Unsupported database schema. Set DATABASE_PATH to a new file; no legacy migrations are provided.')
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript(SCHEMA)
            db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')

    def replace(self, snapshot: Snapshot, timestamp: str):
        # Validate again at the persistence boundary, including mutated containers.
        snapshot = Snapshot.model_validate(snapshot.model_dump())
        records = {lesson.id: lesson for lesson in snapshot.lessons}
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM lessons')
            db.execute('DELETE FROM groups')
            db.executemany('INSERT INTO groups VALUES(?,?)', [(g.id, g.model_dump_json()) for g in snapshot.groups])
            db.executemany('INSERT INTO lessons VALUES(?,?,?,?)',
                           [(l.id, l.group_id, l.date.isoformat(), l.model_dump_json()) for l in records.values()])
            db.execute('''UPDATE sync_state SET revision=?,source=?,coverage=?,last_success=?,last_attempt=?,last_error=NULL,warnings=? WHERE singleton=1''',
                       (uuid.uuid4().hex, snapshot.source.model_dump_json(), snapshot.coverage.model_dump_json(),
                        timestamp, timestamp, json.dumps(snapshot.warnings, ensure_ascii=False)))

    def failure(self, timestamp, message):
        with self.connect() as db:
            db.execute('UPDATE sync_state SET last_attempt=?,last_error=? WHERE singleton=1', (timestamp, message))

    @staticmethod
    def _state(db):
        row = dict(db.execute('SELECT * FROM sync_state WHERE singleton=1').fetchone())
        row.pop('singleton')
        row['source'] = SourceInfo.model_validate_json(row['source']) if row['source'] else None
        row['coverage'] = Coverage.model_validate_json(row['coverage']) if row['coverage'] else None
        row['warnings'] = json.loads(row['warnings'])
        return row

    def status(self):
        with self.connect() as db:
            db.execute('BEGIN')
            return Status(**self._state(db), group_count=db.execute('SELECT COUNT(*) FROM groups').fetchone()[0],
                          lesson_count=db.execute('SELECT COUNT(*) FROM lessons').fetchone()[0])

    def catalog(self):
        with self.connect() as db:
            db.execute('BEGIN')
            return Catalog(revision=self._state(db)['revision'],
                           groups=[Group.model_validate_json(r[0]) for r in db.execute('SELECT payload FROM groups ORDER BY id')])

    def schedule(self, group_id: str, window: Window):
        with self.connect() as db:
            db.execute('BEGIN')
            state = self._state(db)
            row = db.execute('SELECT payload FROM groups WHERE id=?', (group_id,)).fetchone()
            group = Group.model_validate_json(row[0]) if row else None
            coverage = state['coverage']
            lessons = [Lesson.model_validate_json(r[0]) for r in db.execute(
                'SELECT payload FROM lessons WHERE group_id=? AND date BETWEEN ? AND ? ORDER BY date,id',
                (group_id, window.start.isoformat(), window.end.isoformat()))]
            return Schedule(revision=state['revision'], group=group, source=state['source'], coverage=coverage,
                            window=window, available_dates=[d for d in window.dates() if group and coverage and coverage.includes(d)],
                            lessons=lessons, warnings=state['warnings'])
