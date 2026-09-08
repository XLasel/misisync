"""Group navigation metadata, kept separate from the lesson parser."""
import re
from urllib.parse import urlparse

# Direct-file imports lack the HTML link label. These are the published MISIS
# filename prefixes verified on 2026-09-08; unknown sources remain unclassified.
INSTITUTES = {
    'ibo': 'Институт базового образования',
    'bioinzh': 'Институт биомедицинской инженерии',
    'gi': 'Горный институт',
    'itkn': 'Институт компьютерных наук',
    'pish-mast': 'Институт МАСТ',
    'inmin': 'Институт новых материалов',
    'ekoteh': 'Институт технологий',
    'eupp': 'Институт экономики и управления',
    'tfikt': 'Институт физики и квантовой инженерии',
}


def institute_name(url, label=''):
    label = ' '.join(label.split())
    if 'институт' in label.lower():
        return label
    filename = urlparse(url).path.rsplit('/', 1)[-1].lower()
    return next((name for prefix, name in INSTITUTES.items() if filename.startswith(prefix + '-')), '')


def education_level(group):
    # This is a documented code-based classification, not an attribute of a user.
    return {'Б': 'Бакалавриат', 'М': 'Магистратура', 'С': 'Специалитет', 'А': 'Аспирантура'}.get(group[:1].upper(), '')


def subgroup_ids(label):
    """Empty/unrecognized labels remain visible to every subgroup."""
    label = label.strip()
    if not label:
        return []
    match = re.fullmatch(r'(\d+(?:\s*[,и]\s*\d+)*)\s*(?:п\.?\s*г\.?|подгрупп[аы]?)?', label, re.I)
    if not match:
        return []
    return sorted({int(x) for x in re.findall(r'\d+', match.group(1))})
