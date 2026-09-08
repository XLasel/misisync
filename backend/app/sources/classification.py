"""Group navigation metadata shared by schedule adapters."""
import re


def education_level(group):
    # Documented group-code prefix, not an attribute of a logged-in user.
    return {'Б': 'Бакалавриат', 'М': 'Магистратура', 'С': 'Специалитет', 'А': 'Аспирантура'}.get(group[:1].upper(), '')


def subgroup_ids(label):
    """Empty/unrecognized labels remain visible to every subgroup filter."""
    label = label.strip()
    if not label:
        return []
    match = re.fullmatch(r'(\d+(?:\s*[,и]\s*\d+)*)\s*(?:п\.?\s*г\.?|подгрупп[аы]?)?', label, re.I)
    if not match:
        return []
    return sorted({int(x) for x in re.findall(r'\d+', match.group(1))})
