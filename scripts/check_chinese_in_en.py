import json
import re

trials = json.load(open('data/trials.json', encoding='utf-8'))
zh_pattern = re.compile(r'[\u4e00-\u9fa5]')

fields_to_check = ['indication_en', 'drug_name_en', 'sponsor_en', 'lead_institution_en', 'principal_investigator_en']

print(f'Total trials: {len(trials)}')

for f in fields_to_check:
    raw_f = f.replace('_en', '')
    empty = [t for t in trials if not t.get(f) or not str(t.get(f)).strip()]
    print(f'Field {f} EMPTY: {len(empty)}/{len(trials)}')
    for t in empty:
        print(f"  EMPTY {t['registration_id']}: {f} is empty! raw = '{t.get(raw_f)}'")

    bad = [t for t in trials if zh_pattern.search(str(t.get(f, '')))]
    print(f'Field {f} with Chinese characters: {len(bad)}/{len(trials)}')
    for t in bad:
        print(f"  CHINESE {t['registration_id']}: {f} = '{t.get(f)}' | raw = '{t.get(raw_f)}'")
