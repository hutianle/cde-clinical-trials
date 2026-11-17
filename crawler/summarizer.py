import os
import json
import re

# Standard medical translation dictionaries for regulatory & clinical terminology
PHASE_MAP = {
    "I期": "Phase I",
    "II期": "Phase II",
    "III期": "Phase III",
    "IV期": "Phase IV",
    "I/II期": "Phase I/II",
    "II/III期": "Phase II/III",
    "Ia期": "Phase Ia",
    "Ib期": "Phase Ib",
    "IIa期": "Phase IIa",
    "IIb期": "Phase IIb",
    "生物等效性试验": "Bioequivalence (BE)",
    "BE试验": "Bioequivalence (BE)",
    "其他": "Early Phase / Other"
}

STATUS_MAP = {
    "进行中 尚未招募": "Recruiting - Not Yet Open",
    "进行中 招募中": "Active - Recruiting",
    "进行中 招募完成": "Active - Enrollment Completed",
    "已完成": "Completed",
    "主动暂停": "Suspended",
    "终止": "Terminated"
}

DRUG_TYPE_MAP = {
    "化学药物": "Chemical / Small Molecule",
    "生物制品": "Biologic / Large Molecule",
    "中药/天然药物": "Traditional Chinese Medicine (TCM) / Natural",
    "疫苗": "Vaccine"
}

def determine_new_drug(raw_trial: dict) -> bool:
    """
    Classify whether a trial is an innovative/new drug trial vs generic BE study.
    """
    text = " ".join([
        raw_trial.get("phase", ""),
        raw_trial.get("title_lay", ""),
        raw_trial.get("title_professional", ""),
        raw_trial.get("drug_name", "")
    ]).lower()

    if "生物等效性" in text or "be试验" in text or "bioequivalence" in text:
        return False
    return True

def fallback_summarize(trial: dict) -> dict:
    """
    Rule-based intelligent translation and executive summary fallback
    when no Gemini API key is configured.
    """
    is_new = determine_new_drug(trial)
    phase_zh = trial.get("phase", "其他")
    phase_en = PHASE_MAP.get(phase_zh, phase_zh)
    
    status_zh = trial.get("status", "")
    status_en = STATUS_MAP.get(status_zh, status_zh)

    drug_type_zh = trial.get("drug_type", "化学药物")
    drug_type_en = DRUG_TYPE_MAP.get(drug_type_zh, drug_type_zh)

    drug_name = trial.get("drug_name", "")
    indication = trial.get("indication", "")
    sponsor = trial.get("sponsor", "")
    sample_size = trial.get("target_sample_size", "Not specified")
    lead_inst = trial.get("lead_institution", "Not specified")

    # Modality detection
    modality = drug_type_en
    if "抗体" in drug_name or "单抗" in drug_name:
        modality = "Monoclonal Antibody (mAb)"
    elif "细胞" in drug_name or "til" in drug_name.lower() or "car-t" in drug_name.lower():
        modality = "Cell Therapy (TIL/CAR-T)"
    elif "mrna" in drug_name.lower() or "rbd" in drug_name.lower() or "rnai" in drug_name.lower():
        modality = "RNA / Nucleic Acid Therapeutic"
    elif "注射液" in drug_name:
        modality = "Injectable Formulation"

    if is_new:
        category_tag = "Innovative New Drug"
        bullets = [
            f"**Candidate & Modality:** {drug_name} ({modality}), sponsored by {sponsor}.",
            f"**Target Indication:** Investigated for {indication}.",
            f"**Clinical Trial Protocol:** {phase_en} clinical evaluation enrolling an estimated {sample_size} participants.",
            f"**Study Setting:** Conducted at leading trial sites including {lead_inst} under China CDE supervision."
        ]
    else:
        category_tag = "Generic Bioequivalence (BE)"
        bullets = [
            f"**Generic Formulation:** Bioequivalence study for {drug_name} ({modality}).",
            f"**Reference Indication:** Indicated for {indication}.",
            f"**Study Design:** Pharmacokinetic (PK) bioequivalence assessment in healthy volunteers (Target cohort: {sample_size}).",
            f"**Sponsorship & Site:** Sponsored by {sponsor}, conducted at {lead_inst}."
        ]

    return {
        "drug_name_en": drug_name,
        "indication_en": indication,
        "sponsor_en": sponsor,
        "phase_en": phase_en,
        "status_en": status_en,
        "drug_type_en": drug_type_en,
        "is_new_drug": is_new,
        "category_tag": category_tag,
        "executive_summary": "\n\n".join(bullets)
    }

def summarize_with_gemini(trial: dict, api_key: str) -> dict:
    """
    Call Gemini API to generate professional medical translations & executive summaries.
    """
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""You are a pharmaceutical intelligence analyst and regulatory expert on China CDE / NMPA drug clinical trials.
Analyze this newly registered clinical trial from China's CDE registry:

- Registration ID: {trial.get('registration_id')}
- Drug Name: {trial.get('drug_name')}
- Drug Type: {trial.get('drug_type')}
- Indication: {trial.get('indication')}
- Sponsor: {trial.get('sponsor')}
- Trial Phase: {trial.get('phase')}
- Status: {trial.get('status')}
- Lay Title: {trial.get('title_lay')}
- Professional Title: {trial.get('title_professional')}
- Sample Size: {trial.get('target_sample_size')}
- Lead Institution / PI: {trial.get('lead_institution')} / {trial.get('principal_investigator')}
- Primary Endpoints: {trial.get('primary_endpoints')}

Please return a strict JSON object with these exact keys:
{{
  "drug_name_en": "Professional English drug name or code name (e.g. RBD4059 Injection or Rupatadine Fumarate)",
  "indication_en": "Concise medical English translation of the target disease/condition",
  "sponsor_en": "Official or clean English company name of the sponsor",
  "phase_en": "Phase I / Phase II / Phase III / Phase IV / Bioequivalence (BE)",
  "status_en": "Recruiting / Not yet recruiting / Active / Completed",
  "drug_type_en": "Small Molecule / Biologic / Cell & Gene Therapy / TCM / Vaccine",
  "is_new_drug": true if this is an innovative or new drug trial (Phase 1-4) or false if this is purely a generic bioequivalence (BE) study,
  "category_tag": "Innovative New Drug" or "Generic Bioequivalence (BE)",
  "executive_summary": "4 bullet points formatted as markdown:
- **Drug Profile & Modality:** [Drug name, mechanism of action/modality, sponsor]
- **Target Indication:** [Target patient population and unmet medical need]
- **Study Protocol & Scale:** [Phase, cohort size, control design, primary clinical/PK endpoints]
- **Clinical & Commercial Impact:** [Significance in China's pipeline, competitive context, or development milestone]"
}}
Ensure the JSON is strictly valid with no markdown code fences."""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        text = response.text.strip()
        # Clean potential markdown fences
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        return data
    except Exception as e:
        print(f"Gemini API call failed or timed out: {e}. Falling back to rule-based summarizer.")
        return fallback_summarize(trial)

def process_trial(trial: dict) -> dict:
    """
    Main entry point: enriches a raw trial dictionary with translations and executive summary.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        enriched = summarize_with_gemini(trial, api_key)
    else:
        enriched = fallback_summarize(trial)

    # Merge enriched fields into trial record
    merged = {**trial, **enriched}
    return merged
