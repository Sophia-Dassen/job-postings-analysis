"""
Extract skill standardization pipeline tables from an Excel workbook

This script extracts tables from an Excel workbook containing a skill 
standardization pipeline that transforms raw job posting skill mentions 
into standardized skills with hierarchical classifications using a 
controlled skill taxonomy.

The extracted tables are used in downstream analytical processing, enabling 
category-based analysis of skill frequencies and co-occurrences.

Input
-----
Excel skill standardization pipeline workbook containing the following named Excel tables: 
- "RawSkillStandardization": extracted skill mentions with preliminary and 
  final standardizations, including row-level validation metadata
- "SkillTaxonomy": standardized skills with a classification hierarchy of skill
  type, category, and subcategory, including row-level validation metadata
- "SkillClassifications": approved skill type, category, and subcategory combinations 
  used to validate the taxonomy

Output
------
- CSV export of the RawSkillStandardization table with the fields:
  [job_id, extracted_skill, observed_skill_type, preliminary_skill, standardized_skill, 
  valid_mapping, error_message]
- CSV export of the SkillTaxonomy table with the fields:
  [standardized_skill, skill_type, skill_category, skill_subcategory, 
  valid_standardized_skill, valid_classification, error_message]
- CSV export of the SkillClassifications table with the fields:
  [skill_type, skill_category, skill_subcategory]
- JSON file containing extraction run summary
"""

import json
import sys
import warnings
from dataclasses import asdict, dataclass

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import range_boundaries


warnings.filterwarnings(
    "ignore",
    message="Data Validation extension is not supported and will be removed"
)

warnings.filterwarnings(
    "ignore",
    message="Slicer List extension is not supported and will be removed"
)


# ==============================
# SCHEMA DEFINITIONS
# ==============================

# Required fields of the raw skill standardization table.
RAW_SKILL_STANDARDIZATION_FIELDS = [
    "job_id",
    "extracted_skill",	
    "observed_skill_type",	
    "preliminary_skill",	
    "standardized_skill",	
    "valid_mapping",
    "error_message"
]

# Required fields of the skill taxonomy table.
SKILL_TAXONOMY_FIELDS = [
    "standardized_skill",
    "skill_type",
    "skill_category",
    "skill_subcategory",
    "valid_standardized_skill",
    "valid_classification",	
    "error_message"
]

# Required fields of the skill classifications table.
SKILL_CLASSIFICATION_FIELDS = [
    "skill_type",
    "skill_category",
    "skill_subcategory"
]


# ==============================
# CONFIGURATION
# ==============================

WORKBOOK_PATH = "data/source/skill_standardization_pipeline.xlsx"

EXPORT_TABLES = (
    {
        "sheet_name": "raw_to_prelim_mapping",
        "table_name": "RawSkillStandardization",
        "output_path": "data/extracted_demo/raw_to_standardized_skills.csv",
        "expected_fields": RAW_SKILL_STANDARDIZATION_FIELDS,
        "ignored_helper_fields": []
    },
    {
        "sheet_name": "skill_taxonomy",
        "table_name": "SkillTaxonomy",
        "output_path": "data/extracted_demo/skill_taxonomy.csv",
        "expected_fields": SKILL_TAXONOMY_FIELDS,
        "ignored_helper_fields": ["cleaned_standardized_skill"]
    },
    {
        "sheet_name": "skill_classification_lookup",
        "table_name": "SkillClassifications",
        "output_path": "data/extracted_demo/skill_classifications.csv",
        "expected_fields": SKILL_CLASSIFICATION_FIELDS,
        "ignored_helper_fields": []
    },
)

# Extraction summary JSON
SUMMARY_OUTPUT_PATH = "data/extracted_demo/skill_standardization_extraction_summary.json"


# ==============================
# SUMMARY JSON OUTPUT
# ==============================

@dataclass
class ExtractionSummary:
    total_mappings: int
    valid_mappings: int
    invalid_mappings: int
    skill_taxonomy_records: int
    skill_classifications: int


# ==============================
# FUNCTIONS
# ==============================

def extract_excel_table(workbook, sheet_name, table_name):
    """Extract a named Excel table into a DataFrame.

    Args:
        workbook (Workbook): Loaded Excel workbook.
        sheet_name (str): Name of the worksheet containing the table.
        table_name (str): Name of the table to extract.

    Returns:
        pandas.DataFrame: DataFrame containing the extracted table rows
    """

    # Get the table range reference
    worksheet = workbook[sheet_name]
    table = worksheet.tables[table_name]
    ref = table.ref

    # Extract table data
    min_col, min_row, max_col, max_row = range_boundaries(ref)

    rows = list(
        worksheet.iter_rows(
            min_row=min_row,
            max_row=max_row,
            min_col=min_col,
            max_col=max_col,
            values_only=True
        )
    )

    # Construct DataFrame from extracted table rows
    header_row = rows[0]
    data_rows = rows[1:]
    
    return pd.DataFrame(
        data_rows, 
        columns=header_row
    )


def validate_table_fields(extracted_table, expected_fields, ignored_helper_fields):
    """Validate table fields against an expected schema and filter the exported columns.

    Args:
        extracted_table (DataFrame): DataFrame containing extracted table rows
        expected_fields (list): Ordered list of required table fields.
        ignored_helper_fields (list): List of helper fields allowed in the source table but excluded from the export.

    Returns:
        pandas.DataFrame: DataFrame containing the validated table with only expected fields.
    
    Raises:
        ValueError: If required fields are missing or unexpected non-helper fields are present.
    """
    
    headers = extracted_table.columns.tolist()

    unexpected_fields = set(headers) - set(expected_fields) - set(ignored_helper_fields)

    if unexpected_fields:
        raise ValueError(f"Failed to extract table due to unexpected field(s): {unexpected_fields}")
    
    for field in expected_fields:
        if field not in headers:
            raise ValueError(f"Failed to extract table due to missing expected field: {field}")
            
    return extracted_table[expected_fields] 


# ==============================
# PIPELINE EXECUTION
# ==============================

def main():
    
    # Load workbook
    try:
        workbook = load_workbook(
            WORKBOOK_PATH, 
            data_only=True
        )
        print(f"\nSuccessfully loaded workbook: {WORKBOOK_PATH}")
        print('=' * 50)

    except Exception as e:
        print(f"\nFailed to load workbook: {WORKBOOK_PATH}"
              f"\nReason: {e}")
        
        return 1

    total_mappings = 0
    valid_mappings = 0
    invalid_mappings = 0
    skill_taxonomy_records = 0
    skill_classifications = 0

    # Batch extract tables
    for export in EXPORT_TABLES:
        
        print(f"\nProcessing table: {export['table_name']}")

        try:
            # Extract table data
            extracted_table = extract_excel_table(
                workbook,
                sheet_name=export["sheet_name"],
                table_name=export["table_name"]
            )

            # Validate table fields
            validated_table = validate_table_fields(
                extracted_table=extracted_table, 
                expected_fields=export["expected_fields"],
                ignored_helper_fields=export["ignored_helper_fields"]
            )
            
            # Write validated table to CSV
            validated_table.to_csv(
                export["output_path"],
                index=False, 
                encoding="utf-8"
            )

            print(f"Successfully extracted into: {export['output_path']}"
                  f"\nRows extracted: {len(validated_table)}")
            

            if export['table_name'] == "RawSkillStandardization":
                total_mappings = len(validated_table)
                valid_mappings = len(validated_table[validated_table['valid_mapping'] == 1])
                invalid_mappings = len(validated_table[validated_table['valid_mapping'] == 0])
            
            elif export['table_name'] == "SkillTaxonomy":
                skill_taxonomy_records = len(validated_table)
            
            elif export['table_name'] == "SkillClassifications":
                skill_classifications = len(validated_table)


        except ValueError as e:
            print(e)
        
        print('-' * 50)
        
        
    summary = ExtractionSummary(
        total_mappings=total_mappings,
        valid_mappings=valid_mappings,
        invalid_mappings=invalid_mappings,
        skill_taxonomy_records=skill_taxonomy_records,
        skill_classifications=skill_classifications
    )

    with open(
        SUMMARY_OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(asdict(summary), file, indent=4)
    

    return 0


if __name__ == "__main__":
    sys.exit(main())

