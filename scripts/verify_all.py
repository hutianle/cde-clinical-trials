import json
from pathlib import Path

data_trials = json.loads(Path('data/trials.json').read_text(encoding='utf-8'))
web_trials = json.loads(Path('web/data/trials.json').read_text(encoding='utf-8'))

print('=== DATA INTEGRITY VERIFICATION ===')
print(f'data/trials.json count: {len(data_trials)}')
print(f'web/data/trials.json count: {len(web_trials)}')
assert len(data_trials) == 64
assert len(web_trials) == 64

# Check identity
data_ids = [t['registration_id'] for t in data_trials]
web_ids = [t['registration_id'] for t in web_trials]
assert data_ids == web_ids

# 1. Lead institution & PI
empty_inst = [t['registration_id'] for t in data_trials if not t.get('lead_institution')]
empty_pi = [t['registration_id'] for t in data_trials if not t.get('principal_investigator')]
empty_inst_en = [t['registration_id'] for t in data_trials if not t.get('lead_institution_en')]
empty_pi_en = [t['registration_id'] for t in data_trials if not t.get('principal_investigator_en')]

print(f'Empty lead_institution: {len(empty_inst)}/64')
print(f'Empty principal_investigator: {len(empty_pi)}/64')
print(f'Empty lead_institution_en: {len(empty_inst_en)}/64')
print(f'Empty principal_investigator_en: {len(empty_pi_en)}/64')
assert len(empty_inst) == 0
assert len(empty_pi) == 0
assert len(empty_inst_en) == 0
assert len(empty_pi_en) == 0

# 2. Per-trial CDE URL
distinct_urls = len(set(t.get('cde_url') for t in data_trials))
print(f'Distinct cde_url: {distinct_urls}/64')
assert distinct_urls == 64
for t in data_trials:
    assert 'clinicaltrials.searchlistdetail.dhtml?id=' in t['cde_url'], f"Invalid URL: {t['cde_url']}"

# 3. Phase check
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
    elif 'Ib/II期' in p and p_en != 'Phase Ib/II':
        mismatches.append((t['registration_id'], p, p_en))
    elif p == 'I期' and p_en != 'Phase I':
        mismatches.append((t['registration_id'], p, p_en))
    elif p == 'II期' and p_en != 'Phase II':
        mismatches.append((t['registration_id'], p, p_en))
    elif p == 'III期' and p_en != 'Phase III':
        mismatches.append((t['registration_id'], p, p_en))
    elif p == 'IV期' and p_en != 'Phase IV':
        mismatches.append((t['registration_id'], p, p_en))

print(f'Dirty raw phases: {len(dirty_raw)}')
print(f'Phase mismatches: {len(mismatches)}')
assert len(dirty_raw) == 0
assert len(mismatches) == 0

# 4. New drug filter check
non_new = [t['registration_id'] for t in data_trials if not t.get('is_new_drug', True)]
print(f'Non-new drug trials: {len(non_new)}')
assert len(non_new) == 0
assert 'CTR20264163' not in data_ids

print('\nALL CHECKS PASSED!')
