"""
Extracts highlighted skill phrases from multiple annotated job postings.

This script loops over a directory of job posting (.docx) files, extracts all 
highlighted hard and soft skill phrases per job posting, and writes the results 
to a central CSV file.

- Input: Directory containing annotated Word documents with the same structure 
         (job ID in the metadata header and highlighted skill phrases in the job 
         posting excerpt)
- Output: A single CSV file with the fields (job_id, extracted_skill, skill_type)

Notes:
- Highlight color determines the skill classification (hard vs soft)

"""


from docx import Document
from docx.enum.text import WD_COLOR
import csv
import os


# --- CONFIG ---
# Path to the directory containing all annotated job postings
DIR_PATH = "2_Annotated_Job_Postings"

# Output CSV file 
OUTPUT_PATH = "extracted_skills.csv"

# List of all extracted skills 
all_rows = []

# --- COLOR MAPPING ---
COLOR_TO_SKILL = {
    WD_COLOR.TURQUOISE: "hard",
    WD_COLOR.PINK: "soft"
}


# Batch skill extraction 
for filename in os.listdir(DIR_PATH):
    
    if not filename.lower().endswith(".docx"):
        continue # skip non-Word files

    
    # --- OPEN DOCUMENT ---
    doc_path = os.path.join(DIR_PATH, filename)
    doc = Document(doc_path)


    # --- EXTRACT JOB ID ---
    job_id = None
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith("Job ID:"):
            job_id = paragraph.text.replace("Job ID:", "").strip()
            break

    # Raise exception on missing Job ID
    if job_id is None or not job_id:
        raise ValueError(f'Job ID not found in file "{filename}".')


    # --- EXTRACT SKILLS ---
    for paragraph in doc.paragraphs:
        buffer = ""
        skill_type = None

        for run in paragraph.runs:
            if run.font.highlight_color is not None:
                buffer += run.text
                skill_type = COLOR_TO_SKILL.get(run.font.highlight_color, "invalid")
            else: 
                if buffer.strip():
                    all_rows.append({
                        "job_id": job_id, 
                        "extracted_skill": buffer.strip(), 
                        "skill_type": skill_type
                    })
                    buffer = ""
                    skill_type = None

        # flush at end of paragraph
        if buffer.strip():
            all_rows.append({
                "job_id": job_id, 
                "extracted_skill": buffer.strip(), 
                "skill_type": skill_type
            })


# --- WRITE TO CSV ---
with open(OUTPUT_PATH, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["job_id", "extracted_skill", "skill_type"]
    )
    writer.writeheader()
    writer.writerows(all_rows)
