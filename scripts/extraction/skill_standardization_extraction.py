"""
Extract standardized skill taxonomy from Excel worksheet

This script extracts a standardized skill taxonomy from an Excel worksheet 
that was manually curated from raw skill phrases extracted from a collection
of job postings. Each standardized skill has a canonical skill type (hard or 
soft), a skill category, and an optional skill subcategory. 

The extracted skill taxonomy is used in the downstream analysis of skill 
requirements, enabling category-based analysis of skill frequencies and 
co-occurrences.

Input:
------
Excel worksheet containing the skill taxonomy table with the column headers:
[standardized_skill, canonical_skill_type, skill_category, skill_subcategory]

Output:
-------
CSV file containing extracted skill standardizations and categorizations with 
the fields: 
[standardized_skill, canonical_skill_type, skill_category, skill_subcategory]
"""


import sys

import pandas as pd


INPUT_PATH = "data/raw/skill_interpretation.xlsx"
INPUT_SHEET_NAME = "skill_standardization"
OUTPUT_PATH = "data/extracted/extracted_skill_standardization.csv"

# --- SKILL TAXONOMY SCHEMA ---
# Fields defining the standardized skill taxonomy dataset.
SKILL_TAXONOMY_FIELDS = [
    "standardized_skill",
    "canonical_skill_type",
    "skill_category",
    "skill_subcategory"
]

# --- PIPELINE EXECUTION ---
def main():
    
    # Import Excel sheet containing the skill taxonomy table
    df = pd.read_excel(
        INPUT_PATH, 
        sheet_name=INPUT_SHEET_NAME,
        header=1
    )

    # Keep only the columns of the skill taxonomy table
    df_filtered = df[SKILL_TAXONOMY_FIELDS]

    # Write extracted rows to CSV 
    df_filtered.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8"
    )

    return 0

if __name__ == "__main__":
    sys.exit(main())

