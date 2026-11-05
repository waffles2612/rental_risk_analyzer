"""Automated risk-clause detection and explanation for rental agreements."""
from .ingest import Clause, read_document, segment
from .pipeline import Analyzer

__all__ = ["Analyzer", "Clause", "read_document", "segment"]
__version__ = "0.1.0"
