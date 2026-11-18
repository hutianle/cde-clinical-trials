import json

trials = json.load(open('data/trials.json', encoding='utf-8'))
print(f"Loaded {len(trials)} trials.")

for t in trials:
    rid = t['registration_id']
    for k in ['indication_en', 'drug_name_en', 'sponsor_en', 'lead_institution_en', 'principal_investigator_en']:
        val = t.get(k, '')
        raw_k = k.replace('_en', '')
        raw_val = t.get(raw_k, '')
        if not val or not str(val).strip():
            print(f"EMPTY: [{rid}] {k}: raw='{raw_val}'")
        elif any(bad in val for bad in ['()', 'BiotechCo., Ltd.', 'UniversityHospital', 'HospitalHospital', 'PharmaceuticalCo., Ltd.']):
            print(f"DEGRADED: [{rid}] {k}: '{val}' | raw='{raw_val}'")
