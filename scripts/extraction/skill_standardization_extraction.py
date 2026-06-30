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

from openpyxl import load_workbook
from openpyxl.utils import range_boundaries
import pandas as pd


INPUT_PATH = "data/raw/skill_interpretation.xlsx"
INPUT_SHEET_NAME = "skill_taxonomy"
OUTPUT_PATH = "data/extracted/extracted_skill_taxonomy.csv"

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
    
    # Get the range reference of the SkillTaxonomy table
    wb = load_workbook(INPUT_PATH, data_only=True)
    ws = wb[INPUT_SHEET_NAME]
    table = ws.tables["SkillTaxonomy"]
    ref = table.ref

    # Extract the SkillTaxonomy table's data
    min_col, min_row, max_col, max_row = range_boundaries(ref)

    data = []

    for row in ws.iter_rows(
        min_row=min_row,
        max_row=max_row,
        min_col=min_col,
        max_col=max_col,
        values_only=True
    ):
        data.append(row)

    headers = data[0]
    rows = data[1:]

    df = pd.DataFrame(rows, columns=headers)

    # Write extracted rows to CSV 
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8")

    return 0

if __name__ == "__main__":
    sys.exit(main())

