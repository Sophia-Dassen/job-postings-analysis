import pandas as pd


INPUT_PATH = "data/raw/skill_interpretation.xlsx"
INPUT_SHEET_NAME = "skill_standardization"
OUTPUT_PATH = "data/extracted/extracted_skill_standardization.csv"

df = pd.read_excel(
    INPUT_PATH, 
    sheet_name=INPUT_SHEET_NAME,
    header=1
)

columns_to_keep = [
    "standardized_skill",
    "canonical_skill_type",
    "skill_category",
    "skill_subcategory"
]

df_filtered = df[columns_to_keep]

df_filtered.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8"
)


