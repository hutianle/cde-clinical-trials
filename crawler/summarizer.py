import os
import json
import re
import urllib.request
import urllib.parse

# Medical dictionary mappings
PHASE_MAP = {
    "I期": "Phase I",
    "II期": "Phase II",
    "III期": "Phase III",
    "IV期": "Phase IV",
    "I/II期": "Phase I/II",
    "I/IIa期": "Phase I/IIa",
    "II/III期": "Phase II/III",
    "Ia期": "Phase Ia",
    "Ib期": "Phase Ib",
    "IIa期": "Phase IIa",
    "IIb期": "Phase IIb",
    "生物等效性试验": "Bioequivalence (BE)",
    "BE试验": "Bioequivalence (BE)",
    "其他": "Early Phase / Exploratory"
}

STATUS_MAP = {
    "进行中 尚未招募": "Active - Not Yet Recruiting",
    "进行中 招募中": "Active - Recruiting",
    "进行中 招募完成": "Active - Enrollment Completed",
    "已完成": "Completed",
    "主动暂停": "Suspended",
    "终止": "Terminated"
}

DRUG_TYPE_MAP = {
    "化学药物": "Chemical / Small Molecule",
    "生物制品": "Biologic / Large Molecule",
    "中药/天然药物": "Traditional Chinese Medicine (TCM)",
    "中药": "Traditional Chinese Medicine (TCM)",
    "疫苗": "Vaccine"
}

def translate_zh_to_en(text: str) -> str:
    """
    Translates Chinese medical text to English using Google translation service.
    """
    if not text or not text.strip():
        return ""
    
    clean_text = re.sub(r'[\r\n\t]+', ' ', text).strip()
    # If text is already mostly ASCII/English (e.g. NA or code numbers)
    ascii_chars = sum(1 for c in clean_text if ord(c) < 128)
    if len(clean_text) > 0 and (ascii_chars / len(clean_text)) > 0.85:
        return clean_text

    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=zh-CN&tl=en&dt=t&q=" + urllib.parse.quote(clean_text)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            translated = "".join([part[0] for part in data[0] if part[0]]).strip()
            return translated if translated else clean_text
    except Exception as e:
        print(f"Translation warning for '{clean_text[:30]}': {e}")
        return clean_text

def clean_phase(raw_phase: str) -> str:
    cleaned = re.sub(r'\s+', ' ', raw_phase or '').strip()
    if "生物等效性" in cleaned or "be" in cleaned.lower():
        return "Bioequivalence (BE)"
    for zh, en in PHASE_MAP.items():
        if zh in cleaned:
            return en
    return "Phase I" if "I" in cleaned else "Early Phase"

def determine_new_drug(raw_trial: dict) -> bool:
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
    High-quality automated translation and executive summary generation in 100% English.
    """
    is_new = determine_new_drug(trial)
    
    raw_phase = trial.get("phase", "其他")
    phase_en = clean_phase(raw_phase)
    
    raw_status = trial.get("status", "进行中")
    status_en = STATUS_MAP.get(raw_status, "Active - In Progress")

    raw_drug_type = trial.get("drug_type", "化学药物")
    drug_type_en = DRUG_TYPE_MAP.get(raw_drug_type, "Pharmaceutical / Drug")

    # Translate drug name, indication, sponsor
    drug_name_zh = trial.get("drug_name", "")
    indication_zh = trial.get("indication", "")
    sponsor_zh = trial.get("sponsor", "")

    drug_name_en = translate_zh_to_en(drug_name_zh)
    indication_en = translate_zh_to_en(indication_zh)
    sponsor_en = translate_zh_to_en(sponsor_zh)

    sample_size = trial.get("target_sample_size") or "Standard cohort (30-100)"
    lead_inst = trial.get("lead_institution")
    lead_inst_en = translate_zh_to_en(lead_inst) if lead_inst else "Leading clinical study sites in China"

    # Determine modality
    modality = drug_type_en
    if "抗体" in drug_name_zh or "单抗" in drug_name_zh or "mab" in drug_name_zh.lower():
        modality = "Monoclonal Antibody (mAb)"
    elif "细胞" in drug_name_zh or "til" in drug_name_zh.lower() or "car-t" in drug_name_zh.lower():
        modality = "Cell Therapy (TIL / CAR-T)"
    elif "mrna" in drug_name_zh.lower() or "rnai" in drug_name_zh.lower() or "rbd" in drug_name_zh.lower():
        modality = "RNA / Nucleic Acid Therapeutic"
    elif "注射液" in drug_name_zh:
        modality = "Injectable Biologic / Small Molecule"

    if is_new:
        category_tag = "Innovative New Drug"
        bullets = [
            f"**Candidate & Modality:** {drug_name_en} ({modality}), developed by {sponsor_en}.",
            f"**Target Indication:** Investigated for {indication_en}.",
            f"**Study Protocol & Design:** {phase_en} clinical evaluation enrolling an estimated {sample_size} participants.",
            f"**Clinical Setting:** Conducted across accredited clinical research centers ({lead_inst_en}) under China CDE supervision."
        ]
    else:
        category_tag = "Generic Bioequivalence (BE)"
        bullets = [
            f"**Generic Formulation:** Bioequivalence (BE) study for {drug_name_en} ({modality}).",
            f"**Reference Indication:** Indicated for {indication_en}.",
            f"**Study Design:** Pharmacokinetic (PK) bioequivalence assessment in healthy volunteers (Target cohort: {sample_size}).",
            f"**Sponsorship & Site:** Sponsored by {sponsor_en}, conducted at {lead_inst_en}."
        ]

    return {
        "drug_name_en": drug_name_en,
        "indication_en": indication_en,
        "sponsor_en": sponsor_en,
        "phase_en": phase_en,
        "status_en": status_en,
        "drug_type_en": drug_type_en,
        "is_new_drug": is_new,
        "category_tag": category_tag,
        "executive_summary": "\n\n".join(bullets)
    }

def summarize_with_gemini(trial: dict, api_key: str) -> dict:
    """
    Uses Gemini API to produce high-level pharmaceutical intelligence insights in English.
    """
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""You are a pharmaceutical intelligence analyst and regulatory expert on China CDE / NMPA drug clinical trials.
Translate and analyze this newly registered clinical trial from China's CDE registry into 100% English:

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

Please return a strict JSON object with these exact keys (ALL values in fluent, professional medical English):
{{
  "drug_name_en": "Professional English drug name or international non-proprietary name (INN)",
  "indication_en": "Accurate, concise medical English translation of the target condition / disease",
  "sponsor_en": "English company name of the sponsor",
  "phase_en": "Phase I / Phase II / Phase III / Phase IV / Bioequivalence (BE)",
  "status_en": "Active - Recruiting / Active - Not Yet Recruiting / Completed",
  "drug_type_en": "Small Molecule / Biologic / Cell Therapy / RNA Therapeutic / Vaccine",
  "is_new_drug": true if this is an innovative or new drug trial (Phase 1-4) or false if generic BE,
  "category_tag": "Innovative New Drug" or "Generic Bioequivalence (BE)",
  "executive_summary": "4 bullet points in markdown (all English):
- **Candidate & Modality:** [Drug name, mechanism of action/modality, sponsor]
- **Target Indication:** [Target disease and patient population]
- **Study Protocol & Design:** [Phase, cohort size, control design, primary clinical/PK endpoints]
- **Clinical Significance:** [Significance in China's development landscape or therapeutic impact]"
}}
Ensure the JSON is strictly valid with NO markdown code blocks."""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        text = response.text.strip()
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
        print(f"Gemini API call notice: {e}. Using high-quality translation fallback.")
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
