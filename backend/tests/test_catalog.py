import pytest
from app.sources.classification import education_level, subgroup_ids


@pytest.mark.parametrize('label,expected', [
    ('1 п.г.', [1]), ('1, 3 п.г.', [1, 3]), ('1, 2, 3 п.г.', [1, 2, 3]),
    ('3 подгруппа', [3]), ('', []), ('языковая группа 2', []), ('1 и 2 подгруппы', [1, 2]),
])
def test_subgroup_labels(label, expected):
    assert subgroup_ids(label) == expected


def test_education_level_from_group_code():
    assert education_level('МПИ-26-1') == 'Магистратура'
    assert education_level('БИВТ-26-1') == 'Бакалавриат'
    assert education_level('НЕИЗВЕСТНО') == ''
