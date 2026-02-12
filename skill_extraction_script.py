"""
Extracts highlighted hard and soft skill phrases from a single annotated job posting.

This script parses a single job posting (.docx) file, extracts all highlighted 
hard and soft skill phrases, and appends the results to a central CSV file.

- Input: Annotated Word document with job ID in metadata header and highlighted 
         skill phrases in the job posting excerpt
- Output: Appended to CSV file with the fields (job_id, extracted_skill, skill_type)

Notes:
- Highlight color determines the skill type (hard vs soft)
- The script processes *one* job posting at a time
- Directory-based batch processing is planned for a later version

"""

from docx import Document
from docx.enum.text import WD_COLOR
import csv
import os


# --- CONFIG ---
# Path to a single annotated job posting (example): update this path when processing a new job posting
DOC_PATH = "2_Annotated_Job_Postings/ANN_JP_01_Morgan_Stanley_Data_Analyst.docx"

# Output CSV file (append-only)
OUTPUT_PATH = "extracted_skills.csv"


# --- OPEN DOCUMENT ---
doc = Document(DOC_PATH)


# --- EXTRACT JOB ID ---
job_id = None
for paragraph in doc.paragraphs:
    if paragraph.text.startswith("Job ID:"):
        job_id = paragraph.text.replace("Job ID:", "").strip()
        break


# --- COLOR MAPPING ---
COLOR_TO_SKILL = {
    WD_COLOR.TURQUOISE: "hard",
    WD_COLOR.PINK: "soft"
}


# --- EXTRACT SKILLS ---
extracted_rows = []

for paragraph in doc.paragraphs:
    buffer = ""
    skill_type = None

    for run in paragraph.runs:
        if run.font.highlight_color is not None:
            buffer += run.text
            skill_type = COLOR_TO_SKILL.get(run.font.highlight_color, "invalid")
        else: 
            if buffer.strip():
                extracted_rows.append({
                    "job_id": job_id, 
                    "extracted_skill": buffer.strip(), 
                    "skill_type": skill_type
                })
                buffer = ""
                skill_type = None

    # flush at end of paragraph
    if buffer.strip():
        extracted_rows.append({
            "job_id": job_id, 
            "extracted_skill": buffer.strip(), 
            "skill_type": skill_type
        })


# --- APPEND TO CSV ---
file_exists = os.path.isfile(OUTPUT_PATH)

with open(OUTPUT_PATH, mode="a", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["job_id", "extracted_skill", "skill_type"]
    )
    # write header only once
    if not file_exists:
        writer.writeheader()

    writer.writerows(extracted_rows)
