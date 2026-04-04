import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.placements.interview_prep.utils import load_company_data


def test_load_company_data_falls_back_to_shared_dataset():
    oracle = load_company_data("Oracle")

    assert oracle["company"] == "Oracle"
    assert oracle["experiences"]
    assert oracle["questions"]
    assert oracle["summary"]["difficulty"] == "Medium to High"


def test_load_company_data_returns_empty_shape_for_unknown_company():
    unknown = load_company_data("DefinitelyMissingCo")

    assert unknown["company"] == "DefinitelyMissingCo"
    assert unknown["experiences"] == []
    assert unknown["questions"] == []
