"""Reporting module for the AI CFD Platform."""

from .excel import ExcelReportGenerator, generate_report_for_simulation

__all__ = [
    "ExcelReportGenerator",
    "generate_report_for_simulation",
]