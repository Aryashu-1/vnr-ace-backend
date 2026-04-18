import pandas as pd
import json

def inspect_xlsx(file_path):
    try:
        df = pd.read_excel(file_path)
        print(f"File: {file_path}")
        print(f"Columns: {df.columns.tolist()}")
        print("First 2 rows:")
        print(df.head(2).to_dict(orient='records'))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

inspect_xlsx('data/student_data.xlsx')
