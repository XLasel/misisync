import pytest
from app.sources.classification import education_level, institute_name, subgroup_ids

@pytest.mark.parametrize('label,expected', [
    ('1 п.г.', [1]), ('1, 3 п.г.', [1, 3]), ('1, 2, 3 п.г.', [1, 2, 3]),
    ('3 подгруппа', [3]), ('', []), ('языковая группа 2', []), ('1 и 2 подгруппы', [1, 2]),
])
def test_subgroup_labels(label, expected):
    assert subgroup_ids(label) == expected


def test_classification_uses_label_and_leaves_unknown_source_blank():
    assert institute_name('https://misis.ru/files/newname.xls', 'Институт компьютерных наук') == 'Институт компьютерных наук'
    assert institute_name('https://misis.ru/files/itkn-100926.xls') == 'Институт компьютерных наук'
    assert institute_name('https://misis.ru/files/unknown.xls') == ''
    assert education_level('МПИ-26-1') == 'Магистратура'
    assert education_level('НЕИЗВЕСТНО') == ''
