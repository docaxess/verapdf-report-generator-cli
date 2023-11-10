from pydantic import BaseModel, dataclasses


class ResultModel(BaseModel):
    passed_checks: int
    failed_checks: int
    score_checks: float
    passed_rules: int
    failed_rules: int
    score_rules: float
    report: str
