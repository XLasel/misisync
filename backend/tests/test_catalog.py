import sqlite3
from dataclasses import replace

import pytest

from app.catalog import education_level, institute_name, subgroup_ids
from app.db import Database, SCHEMA
from app.parser import Lesson


@pytest.mark.parametrize('label,expected', [
    ('1 п.г.', [1]), ('1, 3 п.г.', [1, 3]), ('1, 2, 3 п.г.', [1, 2, 3]),
    ('3 подгруппа', [3]), ('', []), ('языковая группа 2', []), ('1 и 2 подгруппы', [1, 2]),
])
def test_subgroup_labels(label, expected):
    assert subgroup_ids(label) == expected


def test_catalog_and_safe_subgroup_filter(tmp_path):
    db = Database(str(tmp_path / 'db.sqlite3'))
    db.initialize()
    common = Lesson('БИВТ-26-1', 0, '09:00', '10:35', 'Лекция')
    rows = [common, replace(common, subject='Практика 1', subgroup='1 подгруппа'),
            replace(common, subject='Практика 2', subgroup='2 подгруппа'),
            replace(common, subject='Практика 1,3', subgroup='1, 3 п.г.'),
            replace(common, subject='Неясная запись', subgroup='языковая группа 2')]
    db.replace(rows, {common.group_name: {'Институт компьютерных наук'}}, 'first', 'url', [])
    assert {l['subject'] for l in db.schedule(common.group_name, subgroup=1)} == {'Лекция', 'Практика 1', 'Практика 1,3', 'Неясная запись'}
    assert {l['subject'] for l in db.schedule(common.group_name, subgroup=3)} == {'Лекция', 'Практика 1,3', 'Неясная запись'}
    assert len(db.schedule(common.group_name)) == 5
    assert db.catalog() == [{'name': common.group_name, 'institutes': ['Институт компьютерных наук'], 'education_level': 'Бакалавриат'}]


def test_schema_upgrade_preserves_old_data(tmp_path):
    path = str(tmp_path / 'old.sqlite3')
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
        connection.execute('INSERT INTO groups(name) VALUES(?)', ('МПИ-26-1',))
        connection.execute("UPDATE sync_state SET last_success='last-good'")
        connection.execute('PRAGMA user_version=1')
    database = Database(path)
    database.initialize()
    database.initialize()
    assert database.status()['last_success'] == 'last-good'
    assert database.catalog() == [{'name': 'МПИ-26-1', 'institutes': [], 'education_level': 'Магистратура'}]


def test_classification_uses_label_and_leaves_unknown_source_blank():
    assert institute_name('https://misis.ru/files/newname.xls', 'Институт компьютерных наук') == 'Институт компьютерных наук'
    assert institute_name('https://misis.ru/files/itkn-100926.xls') == 'Институт компьютерных наук'
    assert institute_name('https://misis.ru/files/unknown.xls') == ''
    assert education_level('МПИ-26-1') == 'Магистратура'
    assert education_level('НЕИЗВЕСТНО') == ''
