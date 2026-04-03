# agents/admissions/services.py

import os
from typing import Dict, Any
from agents.admissions.utils import sanitize_key

class AdmissionsDataService:
    DEPT_DIR = "data/departments"

    @classmethod
    def load_departments_data(cls) -> Dict[str, Any]:
        """
        Loads department information from the data/departments directory.
        """
        departments_data = {}
        if os.path.exists(cls.DEPT_DIR):
            for filename in os.listdir(cls.DEPT_DIR):
                if filename.endswith(".txt"):
                    filepath = os.path.join(cls.DEPT_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            key = sanitize_key(filename)
                            departments_data[key] = {
                                "name": os.path.splitext(filename)[0],
                                "content": content
                            }
                    except Exception as e:
                        print(f"Error reading {filename}: {e}")
        return departments_data
