import json
import re
from pathlib import Path

data_trials = json.loads(Path('data/trials.json').read_text(encoding='utf-8'))
web_trials = json.loads(Path('web/data/trials.json').read_text(encoding='utf-8'))
N = len(data_trials)

print('=== DATA INTEGRITY VERIFICATION ===')
print(f'data/trials.json count: {N}')
print(f'web/data/trials.json count: {len(web_trials)}')
assert len(data_trials) == len(web_trials)
assert N > 0

# Check identity
data_ids = [t['registration_id'] for t in data_trials]
web_ids = [t['registration_id'] for t in web_trials]
assert data_ids == web_ids
assert len(set(data_ids)) == N, f"Duplicate IDs found: {N - len(set(data_ids))}"

# 1. Lead institution & PI
empty_inst = [t['registration_id'] for t in data_trials if not t.get('lead_institution')]
empty_pi = [t['registration_id'] for t in data_trials if not t.get('principal_investigator')]
empty_inst_en = [t['registration_id'] for t in data_trials if not t.get('lead_institution_en')]
empty_pi_en = [t['registration_id'] for t in data_trials if not t.get('principal_investigator_en')]

print(f'Empty lead_institution: {len(empty_inst)}/{N}')
print(f'Empty principal_investigator: {len(empty_pi)}/{N}')
print(f'Empty lead_institution_en: {len(empty_inst_en)}/{N}')
print(f'Empty principal_investigator_en: {len(empty_pi_en)}/{N}')
assert len(empty_inst) == 0, f"Found empty lead_institution: {empty_inst}"
assert len(empty_pi) == 0, f"Found empty principal_investigator: {empty_pi}"
assert len(empty_inst_en) == 0, f"Found empty lead_institution_en: {empty_inst_en}"
assert len(empty_pi_en) == 0, f"Found empty principal_investigator_en: {empty_pi_en}"

# 2. English fields validation: NO empty strings, NO Chinese characters, NO degraded artifacts
zh_pattern = re.compile(r'[\u4e00-\u9fa5]')
for f in ['indication_en', 'drug_name_en', 'sponsor_en', 'lead_institution_en', 'principal_investigator_en']:
    empty_f = [t['registration_id'] for t in data_trials if not t.get(f) or not str(t.get(f)).strip()]
    zh_f = [t['registration_id'] for t in data_trials if zh_pattern.search(str(t.get(f, '')))]
    print(f'Field {f} empty: {len(empty_f)}/{N}, Chinese: {len(zh_f)}/{N}')
    assert len(empty_f) == 0, f"Found empty {f}: {empty_f}"
    assert len(zh_f) == 0, f"Found Chinese in {f}: {zh_f}"

degraded_sponsors = [t['registration_id'] for t in data_trials if any(b in t.get('sponsor_en', '') for b in ['()', '（）', 'BiotechCo., Ltd.', 'PharmaceuticalCo., Ltd.'])]
print(f'Degraded sponsors: {len(degraded_sponsors)}/{N}')
assert len(degraded_sponsors) == 0, f"Found degraded sponsors: {degraded_sponsors}"

# 3. Per-trial CDE URL
distinct_urls = len(set(t.get('cde_url') for t in data_trials))
print(f'Distinct cde_url: {distinct_urls}/{N}')
assert distinct_urls == N
for t in data_trials:
    assert 'clinicaltrials.searchlistdetail.dhtml?id=' in t['cde_url'], f"Invalid URL: {t['cde_url']}"

# 4. Phase check
mismatches = []
dirty_raw = []
for t in data_trials:
    p = t.get('phase', '')
    p_en = t.get('phase_en', '')
    if any(c in p for c in ['其它', '其他说明', '\n', '\t', '\r']):
        dirty_raw.append((t['registration_id'], p))
    # Check consistency
    if 'I/II期' in p and p_en != 'Phase I/II':
        mismatches.append((t['registration_id'], p, p_en))
    elif 'II/III期' in p and p_en != 'Phase II/III':
        mismatches.append((t['registration_id'], p, p_en))
    elif p in ['I期', '1期', 'Ⅰ期'] and p_en != 'Phase I':
        mismatches.append((t['registration_id'], p, p_en))
    elif p in ['II期', '2期', 'Ⅱ期'] and p_en != 'Phase II':
        mismatches.append((t['registration_id'], p, p_en))
    elif p in ['III期', '3期', 'Ⅲ期'] and p_en != 'Phase III':
        mismatches.append((t['registration_id'], p, p_en))
    elif p in ['IV期', '4期', 'Ⅳ期'] and p_en != 'Phase IV':
        mismatches.append((t['registration_id'], p, p_en))

print(f'Dirty raw phases: {len(dirty_raw)}')
print(f'Phase mismatches: {len(mismatches)}')
assert len(dirty_raw) == 0, f"Dirty raw phases found: {dirty_raw}"
assert len(mismatches) == 0, f"Phase mismatches found: {mismatches}"

# 5. New drug filter check
non_new = [t['registration_id'] for t in data_trials if not t.get('is_new_drug', True)]
print(f'Non-new drug trials: {len(non_new)}')
assert len(non_new) == 0
assert 'CTR20264163' not in data_ids

print("\nALL VERIFICATIONS PASSED COMPLETELY!")


print('\nALL CHECKS PASSED!')
