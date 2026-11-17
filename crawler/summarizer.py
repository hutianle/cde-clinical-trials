import os
import json
import re
import urllib.request
import urllib.parse
import pypinyin

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

# Comprehensive Chinese Medical Dictionary for Indications and Regulatory Terms
MEDICAL_TERMS = {
    # Prefixes / Actions
    "用于": "For ",
    "适用于": "Indicated for ",
    "拟用于": "Investigated for ",
    "治疗": "treatment of ",
    "缓解": "relief of ",
    "预防": "prevention of ",
    "改善": "improvement of ",
    "伴有": "with ",
    "引起的": "caused by ",
    "患者": "patients",
    "成人": "adults",
    "儿童": "pediatric patients",
    "老年": "elderly",

    # Metabolic & Endocrine
    "代谢相关脂肪性肝炎": "Metabolic Dysfunction-Associated Steatohepatitis (MASH)",
    "非酒精性脂肪性肝炎": "Non-Alcoholic Steatohepatitis (NASH)",
    "脂肪性肝炎": "Steatohepatitis",
    "脂肪肝": "Fatty Liver Disease",
    "2型糖尿病": "Type 2 Diabetes Mellitus (T2D)",
    "1型糖尿病": "Type 1 Diabetes Mellitus (T1D)",
    "糖尿病性周围神经病理性疼痛": "Diabetic Peripheral Neuropathic Pain (DPNP)",
    "糖尿病": "Diabetes Mellitus",
    "超重和肥胖": "overweight and obesity",
    "肥胖/超重": "obesity/overweight",
    "体重管理": "weight management",
    "肥胖": "Obesity",
    "超重": "Overweight",
    "高尿酸血症": "Hyperuricemia",
    "痛风": "Gout",
    "高脂血症": "Hyperlipidemia",
    "甲状腺功能亢进": "Hyperthyroidism",
    "甲状腺功能减退": "Hypothyroidism",

    # Oncology & Hematology
    "广泛期小细胞肺癌": "Extensive-Stage Small Cell Lung Cancer (ES-SCLC)",
    "局限期小细胞肺癌": "Limited-Stage Small Cell Lung Cancer (LS-SCLC)",
    "小细胞肺癌": "Small Cell Lung Cancer (SCLC)",
    "非小细胞肺癌": "Non-Small Cell Lung Cancer (NSCLC)",
    "肺腺癌": "Lung Adenocarcinoma",
    "肺鳞癌": "Lung Squamous Cell Carcinoma",
    "肺癌": "Lung Cancer",
    "直肠腺癌": "Rectal Adenocarcinoma",
    "直肠癌": "Rectal Cancer",
    "结直肠癌": "Colorectal Cancer (CRC)",
    "结肠癌": "Colon Cancer",
    "胃食管交界处腺癌": "Gastroesophageal Junction (GEJ) Adenocarcinoma",
    "胃腺癌": "Gastric Adenocarcinoma",
    "胃癌": "Gastric Cancer",
    "肝细胞癌": "Hepatocellular Carcinoma (HCC) / Liver Cancer",
    "肝癌": "Liver Cancer",
    "胰腺癌": "Pancreatic Cancer",
    "胰腺导管腺癌": "Pancreatic Ductal Adenocarcinoma (PDAC)",
    "卵巢癌": "Ovarian Cancer",
    "铂耐药复发上皮性卵巢癌": "Platinum-Resistant Recurrent Epithelial Ovarian Cancer",
    "铂耐药卵巢癌": "Platinum-Resistant Ovarian Cancer",
    "输卵管癌": "Fallopian Tube Cancer",
    "腹膜癌": "Peritoneal Cancer",
    "乳腺癌": "Breast Cancer",
    "三阴性乳腺癌": "Triple-Negative Breast Cancer (TNBC)",
    "前列腺癌": "Prostate Cancer",
    "膀胱癌": "Bladder Cancer",
    "肾细胞癌": "Renal Cell Carcinoma (RCC)",
    "头颈鳞癌": "Head and Neck Squamous Cell Carcinoma (HNSCC)",
    "食管鳞癌": "Esophageal Squamous Cell Carcinoma (ESCC)",
    "食管癌": "Esophageal Cancer",
    "黑色素瘤": "Melanoma",
    "多发性骨髓瘤": "Multiple Myeloma (MM)",
    "弥漫大B细胞淋巴瘤": "Diffuse Large B-Cell Lymphoma (DLBCL)",
    "中枢神经系统淋巴瘤": "Central Nervous System (CNS) Lymphoma",
    "霍奇金淋巴瘤": "Hodgkin's Lymphoma",
    "非霍奇金淋巴瘤": "Non-Hodgkin's Lymphoma",
    "淋巴瘤": "Lymphoma",
    "白血病": "Leukemia",
    "急性髓系白血病": "Acute Myeloid Leukemia (AML)",
    "急性淋巴细胞白血病": "Acute Lymphoblastic Leukemia (ALL)",
    "实体瘤": "Solid Tumors",
    "晚期实体瘤": "Advanced Solid Tumors",
    "复发/难治性": "Relapsed/Refractory (R/R)",
    "不可切除或转移性": "Unresectable or Metastatic",
    "转移性": "Metastatic",
    "晚期": "Advanced",
    "恶性肿瘤": "Malignancy",
    "癌症": "Cancer",

    # Immunology & Rheumatology
    "中重度活动性炎症性肠病": "Moderate-to-Severe Active Inflammatory Bowel Disease (IBD)",
    "炎症性肠病": "Inflammatory Bowel Disease (IBD)",
    "克罗恩病": "Crohn's Disease",
    "溃疡性结肠炎": "Ulcerative Colitis",
    "强直性脊柱炎": "Ankylosing Spondylitis (AS)",
    "类风湿关节炎": "Rheumatoid Arthritis (RA)",
    "斑块状银屑病": "Plaque Psoriasis",
    "银屑病关节炎": "Psoriatic Arthritis",
    "银屑病": "Psoriasis",
    "系统性红斑狼疮": "Systemic Lupus Erythematosus (SLE)",
    "狼疮性肾炎": "Lupus Nephritis",
    "特应性皮炎": "Atopic Dermatitis",
    "化脓性汗腺炎": "Hidradenitis Suppurativa",
    "白塞病": "Behcet's Disease",
    "原发性干燥综合征": "Primary Sjogren's Syndrome",
    "特发性炎性肌病": "Idiopathic Inflammatory Myopathy",
    "天疱疮": "Pemphigus",
    "重症肌无力": "Myasthenia Gravis",

    # Cardiovascular & Renal
    "原发性IgA肾病": "Primary IgA Nephropathy (IgAN)",
    "IgA肾病": "IgA Nephropathy (IgAN)",
    "肾小球肾炎": "Glomerulonephritis",
    "肾小球疾病": "Glomerular Diseases",
    "慢性肾脏病": "Chronic Kidney Disease (CKD)",
    "心房颤动": "Atrial Fibrillation (AF)",
    "房颤": "Atrial Fibrillation",
    "心力衰竭": "Heart Failure",
    "高血压": "Hypertension",
    "冠心病": "Coronary Artery Disease",
    "心绞痛": "Angina Pectoris",
    "心肌病": "Cardiomyopathy",
    "脑卒中": "Stroke",
    "卒中预防": "Stroke Prevention",
    "动脉粥样硬化": "Atherosclerosis",

    # Neurology & Psychiatry
    "抑郁症": "Major Depressive Disorder (MDD)",
    "精神分裂症": "Schizophrenia",
    "阿尔茨海默病": "Alzheimer's Disease (AD)",
    "帕金森病": "Parkinson's Disease (PD)",
    "癫痫": "Epilepsy",
    "急性高山病": "Acute Mountain Sickness (AMS)",
    "失眠": "Insomnia",
    "焦虑症": "Anxiety Disorder",
    "肌萎缩侧索硬化": "Amyotrophic Lateral Sclerosis (ALS)",

    # Infectious & Respiratory
    "流行性感冒": "Influenza",
    "甲型和乙型流行性感冒": "Influenza A and B",
    "甲型流感": "Influenza A",
    "乙型流感": "Influenza B",
    "急性支气管炎": "Acute Bronchitis",
    "慢性支气管炎": "Chronic Bronchitis",
    "支气管哮喘": "Bronchial Asthma",
    "哮喘": "Asthma",
    "慢阻肺": "Chronic Obstructive Pulmonary Disease (COPD)",
    "特发性肺纤维化": "Idiopathic Pulmonary Fibrosis (IPF)",
    "肺炎": "Pneumonia",
    "乙型肝炎": "Hepatitis B",
    "丙型肝炎": "Hepatitis C",
    "艾滋病": "HIV/AIDS",
    "带状疱疹": "Herpes Zoster / Shingles",

    # Ophthalmology, ENT & Dermatology
    "视网膜静脉阻塞": "Retinal Vein Occlusion (RVO)",
    "新生血管性年龄相关性黄斑变性": "Neovascular Age-Related Macular Degeneration (nAMD)",
    "黄斑水肿": "Macular Edema",
    "葡萄膜炎": "Uveitis",
    "非感染性葡萄膜炎": "Non-infectious Uveitis",
    "白内障": "Cataract",
    "青光眼": "Glaucoma",
    "干眼症": "Dry Eye Disease",
    "耳聋": "Hearing Loss / Deafness",
    "白癜风": "Vitiligo",
    "脱发": "Alopecia",
    "贫血": "Anemia",

    # Dosage Forms & Modalities
    "注射用": "for Injection",
    "注射液": "Injection",
    "口服溶液": "Oral Solution",
    "缓释片": "Sustained-Release Tablets",
    "肠溶片": "Enteric-Coated Tablets",
    "分散片": "Dispersible Tablets",
    "片剂": "Tablets",
    "片": "Tablets",
    "胶囊剂": "Capsules",
    "胶囊": "Capsules",
    "滴眼液": "Eye Drops",
    "重组人": "Recombinant Human ",
    "单克隆抗体": "Monoclonal Antibody",
    "双特异性抗体": "Bispecific Antibody",
    "抗体偶联药物": "Antibody-Drug Conjugate (ADC)",

    # Corporate & Institutional Suffixes
    "股份有限公司": "Co., Ltd.",
    "责任有限公司": "Co., Ltd.",
    "有限责任公司": "Co., Ltd.",
    "有限公司": "Co., Ltd.",
    "药业集团": "Pharma Group",
    "制药集团": "Pharma Group",
    "制药工程": "Pharmaceutical Engineering",
    "制药科技": "Pharmaceutical Technology",
    "制药": "Pharma",
    "药业": "Pharmaceutical",
    "医药科技": "Pharmaceutical Technology",
    "医药": "Pharmaceuticals",
    "生物科技": "Biotech",
    "生物制药": "Biopharma",
    "生物制品": "Biological Products",
    "生物医药": "Biomedicine",
    "生物": "Bio",
    "科技": "Technology",
    "研究院": "Research Institute",
    "研究所有限公司": "Research Institute Co., Ltd.",
    "研究所": "Research Institute",
    "附属第一医院": "First Affiliated Hospital",
    "附属第二医院": "Second Affiliated Hospital",
    "附属第三医院": "Third Affiliated Hospital",
    "附属肿瘤医院": "Cancer Center / Affiliated Tumor Hospital",
    "附属医院": "Affiliated Hospital",
    "人民医院": "People's Hospital",
    "肿瘤医院": "Cancer Hospital",
    "总医院": "General Hospital",
    "医科大学": "Medical University",
    "医学院": "Medical College",
    "大学": "University",
    "医院": "Hospital"
}

def has_chinese(text: str) -> bool:
    """Checks if a string contains any Chinese character."""
    if not text:
        return False
    return any('\u4e00' <= char <= '\u9fff' for char in str(text))

def dictionary_fallback_translate(text: str) -> str:
    """
    Substitutes medical terms using our rich medical dictionary.
    """
    if not text:
        return ""
    result = text
    # Sort terms by length descending to match longest phrases first
    for cn_term in sorted(MEDICAL_TERMS.keys(), key=len, reverse=True):
        if cn_term in result:
            result = result.replace(cn_term, MEDICAL_TERMS[cn_term])
    return result

def clean_residual_chinese(text: str) -> str:
    """
    Cleans residual punctuation or Chinese characters from translated medical strings.
    """
    if not text:
        return ""
    # Map common Chinese punctuation
    punct_map = {
        "（": " (", "）": ") ", "、": ", ", "，": ", ", "。": ". ", "：": ": ", "；": "; ",
        "／": "/", "【": "[", "】": "]"
    }
    for cn_p, en_p in punct_map.items():
        text = text.replace(cn_p, en_p)
    return re.sub(r'\s+', ' ', text).strip()

def translate_zh_to_en(text: str) -> str:
    """
    Translates Chinese medical text to 100% English:
    1. Pre-checks if already English.
    2. Uses online translation service.
    3. Runs dictionary replacement for any un-translated medical jargon (e.g. MASH, DFNB9, specific oncology targets).
    4. Guarantees clean English output without residual Chinese characters.
    """
    if not text or not text.strip():
        return ""
    
    clean_text = clean_residual_chinese(text)
    if not has_chinese(clean_text):
        return clean_text

    translated = None
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=zh-CN&tl=en&dt=t&q=" + urllib.parse.quote(clean_text)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidate = "".join([part[0] for part in data[0] if part[0]]).strip()
            if candidate:
                translated = candidate
    except Exception as e:
        print(f"Translation API warning for '{clean_text[:30]}': {e}")

    # If API translation still contains Chinese or failed, apply dictionary replacement
    if not translated or has_chinese(translated):
        base_text = translated if translated else clean_text
        translated = dictionary_fallback_translate(base_text)

    # Clean residual Chinese characters if any still remain
    if has_chinese(translated):
        # Final pass: remove any leftover isolated Chinese characters
        translated = re.sub(r'[\u4e00-\u9fff]+', '', translated).strip()

    return clean_residual_chinese(translated)

def romanize_chinese_name(name: str) -> str:
    """
    Romanizes a person's name using standard pinyin if in Chinese characters.
    Properly handles compound surnames (欧阳, 司马, 诸葛, etc.).
    Preserves English/Latin characters. Never invents a translation.
    """
    if not name or not str(name).strip():
        return ""
    clean = str(name).strip()
    # If no Chinese characters, return as is
    if not any('\u4e00' <= c <= '\u9fff' for c in clean):
        return clean
    
    compound_surnames = ["欧阳", "司马", "上官", "诸葛", "皇甫", "东方", "令狐", "申屠", "公孙", "慕容"]
    surname = ""
    given_name = ""
    for cs in compound_surnames:
        if clean.startswith(cs):
            surname = cs
            given_name = clean[len(cs):]
            break
    if not surname:
        surname = clean[0]
        given_name = clean[1:]
    
    sur_pinyin = "".join(pypinyin.lazy_pinyin(surname)).capitalize()
    given_pinyin = "".join(pypinyin.lazy_pinyin(given_name)).capitalize()
    
    if given_pinyin:
        return f"{given_pinyin} {sur_pinyin}"
    return sur_pinyin

def normalize_raw_phase(raw: str) -> str:
    """
    Normalizes dirty raw phase strings from CDE detail pages.
    Strips whitespace/newlines; extracts explanation if wrapped in '其它...其他说明:...';
    converts to canonical Chinese phase representation.
    """
    if not raw:
        return ""
    s = re.sub(r'[\s\r\n\t]+', '', str(raw)).strip()
    if ("其它" in s or "其他" in s) and any(k in s for k in ["说明:", "说明："]):
        m = re.search(r'(?:其他说明|其它说明|说明)[:：](.+)', s)
        if m:
            s = m.group(1).strip()
    
    char_map = {
        'Ⅰ': 'I', 'Ⅱ': 'II', 'Ⅲ': 'III', 'Ⅳ': 'IV',
        'ⅰ': 'i', 'ⅱ': 'ii', 'ⅲ': 'iii', 'ⅳ': 'iv',
        '１': '1', '２': '2', '３': '3', '４': '4',
        '／': '/'
    }
    for k, v in char_map.items():
        s = s.replace(k, v)

    if s in ["I/II期", "I/II", "I期/II期", "I期/II", "I/II期试验"]:
        return "I/II期"
    elif s in ["Ib/II期", "Ib/II", "Ib期/II期", "Ib期/II"]:
        return "Ib/II期"
    elif s in ["Ia/Ib期", "Ia/Ib", "Ia期/Ib期"]:
        return "Ia/Ib期"
    elif s in ["II/III期", "II/III", "II期/III期"]:
        return "II/III期"
    elif s in ["III/IV期", "III/IV", "III期/IV期"]:
        return "III/IV期"
    elif s in ["I期", "1期", "Phase I", "Phase 1"]:
        return "I期"
    elif s in ["II期", "2期", "Phase II", "Phase 2"]:
        return "II期"
    elif s in ["III期", "3期", "Phase III", "Phase 3"]:
        return "III期"
    elif s in ["IV期", "4期", "Phase IV", "Phase 4"]:
        return "IV期"
    elif s in ["Ia期", "Ib期", "Ic期", "IIa期", "IIb期", "IIIa期", "IIIb期"]:
        return s

    if s.endswith("期"):
        return s
    if any(k in s for k in ["I", "II", "III", "IV"]):
        return s + "期"
    return s

def normalize_phase_str(s: str) -> str:
    """Normalizes Roman, full-width, and Chinese numerals in clinical phase strings."""
    if not s:
        return ""
    cleaned = normalize_raw_phase(s)
    char_map = {
        'Ⅰ': 'I', 'Ⅱ': 'II', 'Ⅲ': 'III', 'Ⅳ': 'IV',
        'ⅰ': 'i', 'ⅱ': 'ii', 'ⅲ': 'iii', 'ⅳ': 'iv',
        '１': '1', '２': '2', '３': '3', '４': '4',
        '／': '/', '（': '(', '）': ')', '：': ':'
    }
    for k, v in char_map.items():
        cleaned = cleaned.replace(k, v)
    return cleaned

def clean_phase(raw_phase: str) -> str:
    """
    Translates raw Chinese clinical trial phases to standard English phases.
    Handles full-width numerals (Ⅰ/Ⅱ/Ⅲ/Ⅳ), compound phases (I/II, II/III, Ib/II),
    and descriptive text. Never guesses — leaves unknown values untranslated and flags them.
    """
    if not raw_phase:
        return ""
    
    cleaned = normalize_phase_str(raw_phase)
    
    # 1. Check for Bioequivalence (BE)
    if "生物等效性" in cleaned or re.search(r'\bBE\b', cleaned, re.I):
        return "Bioequivalence (BE)"

    # 2. Check compound and sub-phases in priority order (longest & most specific first)
    patterns = [
        # Compound phase combinations
        (r'\bI/IIa\b|I/IIa期', "Phase I/IIa"),
        (r'\bI/IIb\b|I/IIb期', "Phase I/IIb"),
        (r'\bIa/Ib\b|Ia/Ib期', "Phase Ia/Ib"),
        (r'\bIb/IIa\b|Ib/IIa期', "Phase Ib/IIa"),
        (r'\bIb/II\b|Ib/II期|Ib期/II期|Ib期/II', "Phase Ib/II"),
        (r'\bI/II\b|I/II期|I期/II期|I期/II', "Phase I/II"),
        (r'\bIIa/IIb\b|IIa/IIb期', "Phase IIa/IIb"),
        (r'\bIIa/III\b|IIa/III期', "Phase IIa/III"),
        (r'\bII/III\b|II/III期|II期/III期|II期/III', "Phase II/III"),
        (r'\bIII/IV\b|III/IV期|III期/IV期|III期/IV', "Phase III/IV"),

        # Sub-phases
        (r'\bIa\b|Ia期', "Phase Ia"),
        (r'\bIb\b|Ib期', "Phase Ib"),
        (r'\bIc\b|Ic期', "Phase Ic"),
        (r'\bIIa\b|IIa期', "Phase IIa"),
        (r'\bIIb\b|IIb期', "Phase IIb"),
        (r'\bIIIa\b|IIIa期', "Phase IIIa"),
        (r'\bIIIb\b|IIIb期', "Phase IIIb"),

        # Standard phases (must test IV, III, II before I)
        (r'\bIV\b|IV期|4期|Phase\s*IV|Phase\s*4|四期', "Phase IV"),
        (r'\bIII\b|III期|3期|Phase\s*III|Phase\s*3|三期', "Phase III"),
        (r'\bII\b|II期|2期|Phase\s*II|Phase\s*2|二期', "Phase II"),
        (r'\bI\b|I期|1期|Phase\s*I|Phase\s*1|一期', "Phase I"),

        # Exploratory / Early
        (r'0期|Phase\s*0|探索性|早期临床', "Phase 0 / Exploratory")
    ]

    for pat, label in patterns:
        if re.search(pat, cleaned, re.I):
            return label

    # Never guess — leave unknown values untranslated and flag them
    print(f"[FLAG UNKNOWN PHASE] Could not determine phase for: {repr(raw_phase)}")
    return cleaned

def determine_new_drug(raw_trial: dict) -> bool:
    text = " ".join([
        str(raw_trial.get("phase", "")),
        str(raw_trial.get("title_lay", "")),
        str(raw_trial.get("title_professional", "")),
        str(raw_trial.get("drug_name", "")),
        str(raw_trial.get("indication", ""))
    ]).lower()

    if any(k in text for k in [
        "生物等效性", "be试验", "bioequivalence", "等效性研究", "等效性试验",
        "仿制药", "参比制剂", "双交叉空腹", "受试制剂与参比制剂"
    ]):
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

    drug_name_zh = trial.get("drug_name", "")
    indication_zh = trial.get("indication", "")
    sponsor_zh = trial.get("sponsor", "")

    # Clean English translations
    drug_name_en = translate_zh_to_en(drug_name_zh)
    indication_en = translate_zh_to_en(indication_zh)
    sponsor_en = translate_zh_to_en(sponsor_zh)

    sample_size = trial.get("target_sample_size") or "Standard cohort (30-100)"
    lead_inst = trial.get("lead_institution")
    lead_inst_en = translate_zh_to_en(lead_inst) if lead_inst else "Accredited clinical research centers in China"

    # Modality detection
    modality = drug_type_en
    if "抗体" in drug_name_zh or "单抗" in drug_name_zh or "mab" in drug_name_zh.lower():
        modality = "Monoclonal Antibody (mAb)"
    elif "细胞" in drug_name_zh or "til" in drug_name_zh.lower() or "car-t" in drug_name_zh.lower():
        modality = "Cell Therapy (TIL / CAR-T)"
    elif "mrna" in drug_name_zh.lower() or "rnai" in drug_name_zh.lower() or "rbd" in drug_name_zh.lower():
        modality = "RNA / Nucleic Acid Therapeutic"
    elif "疫苗" in drug_name_zh or "vaccine" in drug_name_zh.lower():
        modality = "Vaccine Formulation"
    elif "注射液" in drug_name_zh:
        modality = "Injectable Therapeutic"

    bullets = [
        f"**Candidate & Modality:** {drug_name_en} ({modality}), developed by {sponsor_en}.",
        f"**Target Indication:** Investigated for {indication_en}.",
        f"**Study Protocol & Design:** {phase_en} clinical evaluation enrolling an estimated {sample_size} participants.",
        f"**Clinical Setting:** Conducted across accredited clinical research centers ({lead_inst_en}) under China CDE supervision."
    ]

    return {
        "drug_name_en": drug_name_en,
        "indication_en": indication_en,
        "sponsor_en": sponsor_en,
        "phase_en": phase_en,
        "status_en": status_en,
        "drug_type_en": drug_type_en,
        "is_new_drug": is_new,
        "category_tag": "Innovative New Drug",
        "executive_summary": "\n\n".join(bullets)
    }

def summarize_with_gemini(trial: dict, api_key: str) -> dict:
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""You are a pharmaceutical intelligence analyst and regulatory expert on China CDE / NMPA drug clinical trials.
Translate and analyze this newly registered innovative new drug clinical trial from China's CDE registry into 100% fluent English (absolutely no Chinese in output):

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

Return a strict JSON object with these exact keys (ALL values in 100% English):
{{
  "drug_name_en": "Professional English drug name or INN",
  "indication_en": "Accurate, concise medical English translation of the target condition / disease",
  "sponsor_en": "English company name of the sponsor",
  "phase_en": "Phase I / Phase II / Phase III / Phase IV",
  "status_en": "Active - Recruiting / Active - Not Yet Recruiting / Completed",
  "drug_type_en": "Small Molecule / Biologic / Cell Therapy / RNA Therapeutic / Vaccine",
  "is_new_drug": true,
  "category_tag": "Innovative New Drug",
  "executive_summary": "4 bullet points in markdown (100% English):
- **Candidate & Modality:** [Drug name, mechanism of action/modality, sponsor]
- **Target Indication:** [Target disease and patient population in English]
- **Study Protocol & Design:** [Phase, cohort size, control design, primary clinical endpoints]
- **Clinical Significance:** [Significance in China's development landscape or therapeutic impact]"
}}
Ensure the JSON is strictly valid with NO markdown code fences."""

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
        print(f"Gemini notice: {e}. Using robust medical translation fallback.")
        return fallback_summarize(trial)

def process_trial(trial: dict) -> dict:
    # Always normalize raw phase string first
    raw_phase = normalize_raw_phase(trial.get("phase", ""))
    trial["phase"] = raw_phase

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        enriched = summarize_with_gemini(trial, api_key)
    else:
        enriched = fallback_summarize(trial)

    # Always guarantee accurate deterministic phase_en translation
    enriched["phase_en"] = clean_phase(raw_phase)
    enriched["is_new_drug"] = determine_new_drug(trial)

    # Safety checks: enforce 100% English across all key fields
    for field in ["indication_en", "drug_name_en", "sponsor_en"]:
        val = enriched.get(field, "")
        if not val or has_chinese(val):
            raw_zh = trial.get(field.replace("_en", ""), val)
            enriched[field] = translate_zh_to_en(raw_zh)

    # Institution and PI translations
    lead_inst = trial.get("lead_institution", "")
    lead_inst_en = trial.get("lead_institution_en")
    if not lead_inst_en or has_chinese(lead_inst_en):
        lead_inst_en = translate_zh_to_en(lead_inst) if lead_inst else ""
    enriched["lead_institution_en"] = lead_inst_en

    pi = trial.get("principal_investigator", "")
    pi_en = trial.get("principal_investigator_en")
    if not pi_en or has_chinese(pi_en):
        pi_en = romanize_chinese_name(pi) if pi else ""
    enriched["principal_investigator_en"] = pi_en

    # Ensure executive summary has accurate phase and no residual Chinese characters
    summary = enriched.get("executive_summary", "")
    if has_chinese(summary) or ("Phase I" in summary and enriched["phase_en"] != "Phase I"):
        # Regenerate summary bullets using clean English fields
        modality = enriched.get("drug_type_en", "Innovative Therapeutic")
        lead_summary = lead_inst_en or "accredited clinical research centers in China"
        bullets = [
            f"**Candidate & Modality:** {enriched.get('drug_name_en')} ({modality}), developed by {enriched.get('sponsor_en')}.",
            f"**Target Indication:** Investigated for {enriched.get('indication_en')}.",
            f"**Study Protocol & Design:** {enriched.get('phase_en')} clinical evaluation enrolling an estimated {trial.get('target_sample_size', 'standard')} participants.",
            f"**Clinical Setting:** Conducted across accredited clinical research centers ({lead_summary}) under China CDE supervision."
        ]
        enriched["executive_summary"] = "\n\n".join(bullets)

    merged = {**trial, **enriched}
    return merged
