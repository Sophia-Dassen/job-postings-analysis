"""
Extracts highlighted skill phrases from multiple annotated job postings.

This script loops over a directory of job posting (.docx) files, extracts all 
highlighted hard and soft skill phrases per job posting, and writes the results 
to a central CSV file.

- Input: Directory containing annotated Word documents with the same structure 
         (job ID in the metadata header and highlighted skill phrases in the job 
         posting excerpt)
- Output: A single CSV file with the fields (job_id, extracted_skill, observed_skill_type)

Notes:
- Highlight color determines the skill classification (hard vs soft)
- Duplicate skills per job posting are not allowed (goal: tracking skill presence, 
  not skill-mention frequency)

"""


from docx import Document
from docx.enum.text import WD_COLOR
import csv
import os


# --- CONFIG ---
# Path to the directory containing all annotated job postings
DIR_PATH = "2_Annotated_Job_Postings"

# Output CSV files
JP_OUTPUT_PATH = "extracted_job_posting_metadata.csv"
SKILL_OUTPUT_PATH = "extracted_skills.csv"

# Lists for extracted job posting metadata and extracted skills
all_jp_metadata_rows = []
all_skill_rows = []


# --- COLOR MAPPING ---
COLOR_TO_SKILL = {
    WD_COLOR.TURQUOISE: "hard",
    WD_COLOR.PINK: "soft"
}

# --- DICT OF METADATA LABELS & OUTPUT FIELDS ---
METADATA_FIELDS = {
    "Job ID": "job_id",
    "Company": "company",
    "Job Title": "job_title",
    "Location": "location",
    "Source Platform": "source_platform",
    "Original URL": "original_url",
    "Date collected": "date_collected"
}

processed_files = 0 # Counter 

# Batch job posting processing 
for filename in os.listdir(DIR_PATH):
    
    if not filename.lower().endswith(".docx"):
        continue # skip non-Word files
    processed_files += 1
    

    # --- OPEN DOCUMENT ---
    doc_path = os.path.join(DIR_PATH, filename)
    doc = Document(doc_path)
    print(f'Processing file: {filename}')


    # --- EXTRACT JOB ID ---
    job_id = None
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith("Job ID:"):
            job_id = paragraph.text.replace("Job ID:", "").strip()
            break
    # Raise exception on missing Job ID
    if job_id is None or not job_id:
        raise ValueError(f'Job ID not found in file "{filename}".')


    metadata = {field: None for field in METADATA_FIELDS.values()}

    # --- EXTRACT JOB POSTING METADATA ---
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()

        for label, field in METADATA_FIELDS.items():
            label_prefix = f'{label}:'
            if text.startswith(label_prefix):
                metadata[field] = text.replace(label_prefix, "", 1).strip()

    all_jp_metadata_rows.append(metadata)


    # Track extracted skills to prevent duplicates per job posting
    extracted_skills = set()


    # --- EXTRACT SKILLS ---
    for paragraph in doc.paragraphs:
        buffer = ""
        observed_skill_type = None

        for run in paragraph.runs:
            if run.font.highlight_color is not None:
                buffer += run.text
                observed_skill_type = COLOR_TO_SKILL.get(run.font.highlight_color, "invalid")
            else: 
                skill_text = buffer.strip()
                if skill_text and skill_text not in extracted_skills:
                    all_skill_rows.append({
                        "job_id": job_id, 
                        "extracted_skill": skill_text, 
                        "observed_skill_type": observed_skill_type
                    })
                    extracted_skills.add(skill_text)
                
                buffer = ""
                observed_skill_type = None

        # flush at end of paragraph
        skill_text = buffer.strip()
        if skill_text and skill_text not in extracted_skills:
            all_skill_rows.append({
                "job_id": job_id, 
                "extracted_skill": skill_text, 
                "observed_skill_type": observed_skill_type
            })
            extracted_skills.add(skill_text)


# --- WRITE JOB POSTING METADATA TO CSV ---
with open(JP_OUTPUT_PATH, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["job_id", "company", "job_title", "location", "source_platform", "original_url", "date_collected"]
    )
    writer.writeheader()
    writer.writerows(all_jp_metadata_rows)


# --- WRITE SKILLS TO CSV ---
with open(SKILL_OUTPUT_PATH, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["job_id", "extracted_skill", "observed_skill_type"]
    )
    writer.writeheader()
    writer.writerows(all_skill_rows)


finished_log_msg = (f'Extraction complete: {len(all_skill_rows)} skills extracted from {processed_files} job postings.')
print("=" * len(finished_log_msg))
print(finished_log_msg)
print("=" * len(finished_log_msg))
