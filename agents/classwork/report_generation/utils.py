# agents/classwork/report_generation/utils.py

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.strip().lower().split())


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_audit_event(
    event_type: str,
    user_id: str,
    agent_name: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "timestamp": utc_now_iso(),
        "event_type": event_type,
        "user_id": user_id,
        "agent_name": agent_name,
        "details": details or {},
    }


def load_csv_dataset(path: str | Path, normalize_cols: bool = True) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset not found: {p}")
    df = pd.read_csv(p)
    if normalize_cols:
        df = normalize_column_names(df)
    return df


def load_datasets_from_registry(
    dataset_names: List[str],
    registry: Dict[str, str],
) -> Dict[str, pd.DataFrame]:
    loaded: Dict[str, pd.DataFrame] = {}
    for name in dataset_names:
        if name not in registry:
            raise ValueError(f"Dataset '{name}' is not registered.")
        loaded[name] = load_csv_dataset(registry[name])
    return loaded


def validate_filter_columns_against_datasets(
    filters: Dict[str, Any],
    dataset_names: List[str],
    dataset_allowed_columns: Dict[str, set],
) -> List[str]:
    allowed_union = set()
    for ds in dataset_names:
        allowed_union.update(dataset_allowed_columns.get(ds, set()))

    invalid = [key for key in filters.keys() if key not in allowed_union]
    return invalid


def apply_dataframe_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    result = df.copy()
    for column, value in filters.items():
        if column not in result.columns:
            raise ValueError(f"Invalid filter column: {column}")
        if value is None:
            continue
        if isinstance(value, str) and pd.api.types.is_object_dtype(result[column]):
            result = result[result[column].astype(str).str.lower() == value.lower()]
            continue
        result = result[result[column] == value]
    return result


def limit_preview_rows(df: pd.DataFrame, limit: int = 20) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    return df.head(limit).to_dict(orient="records")


def dataframe_summary(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
    }


def build_report_filename(report_type: str, extension: str = "xlsx") -> str:
    safe_type = normalize_text(report_type).replace(" ", "_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_type}_{ts}.{extension}"


def export_dataframe(
    df: pd.DataFrame,
    output_dir: str | Path,
    report_type: str,
    extension: str = "xlsx",
) -> str:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = build_report_filename(report_type, extension)
    path = output_dir / filename

    if extension == "csv":
        df.to_csv(path, index=False)
    elif extension == "xlsx":
        df.to_excel(path, index=False)
    else:
        raise ValueError(f"Unsupported export extension: {extension}")

    return str(path)


def join_students_with_attendance(
    students_df: pd.DataFrame,
    attendance_df: pd.DataFrame,
) -> pd.DataFrame:
    return students_df.merge(attendance_df, on="student_id", how="left")


def join_students_with_marks(
    students_df: pd.DataFrame,
    marks_df: pd.DataFrame,
) -> pd.DataFrame:
    return students_df.merge(marks_df, on="student_id", how="left")


def generate_preview_message(
    report_type: str,
    row_count: int,
    preview_rows: List[Dict[str, Any]],
) -> str:
    return (
        f"Preview ready.\n\n"
        f"Report type: {report_type}\n"
        f"Rows found: {row_count}\n"
        f"Preview rows: {preview_rows}\n\n"
        f"Approve to generate the final report."
    )
