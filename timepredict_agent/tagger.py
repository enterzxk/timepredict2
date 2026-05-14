from __future__ import annotations

import re

from .models import Paper


CCF_VENUES = {
    "AAAI": "CCF-A",
    "IJCAI": "CCF-A",
    "NeurIPS": "CCF-A",
    "NIPS": "CCF-A",
    "ICML": "CCF-A",
    "KDD": "CCF-A",
    "SIGIR": "CCF-A",
    "WWW": "CCF-A",
    "ACL": "CCF-A",
    "CVPR": "CCF-A",
    "ICLR": "CCF-B",
    "CIKM": "CCF-B",
    "ICDM": "CCF-B",
    "WSDM": "CCF-B",
    "EMNLP": "CCF-B",
}

TOPIC_PATTERNS = {
    "Long-term forecasting": r"long[- ]term|long horizon|long-range",
    "Probabilistic forecasting": r"probabilistic|uncertainty|quantile|distribution",
    "Foundation model": r"foundation model|large model|pretrain|pre-train",
    "Transformer": r"transformer|attention",
    "Diffusion": r"diffusion|score-based",
    "Multivariate": r"multivariate|multi-variate|cross-channel",
    "Benchmark": r"benchmark|dataset|evaluation",
    "Anomaly detection": r"anomaly|outlier",
    "Spatio-temporal": r"spatio-temporal|spatiotemporal|spatial-temporal",
    "Predictive process monitoring": r"predictive process monitoring|process monitoring|predictive monitoring",
    "Business process": r"business process|process mining|process model",
    "Event sequence": r"event sequence|event log|event stream",
    "Next event prediction": r"next event|event prediction|activity prediction",
    "Remaining time prediction": r"remaining time prediction|remaining time|time prediction|duration prediction",
    "Incremental event log": r"incremental event log|incremental log|evolving event log",
    "Incremental learning": r"incremental|online learning|continual|streaming",
    "Concept drift": r"concept drift|distribution shift|changepoint|non.stationary",
    "Process discovery": r"process discovery|process conformance",
}


def classify_paper(paper: Paper) -> list[str]:
    text = f"{paper.title} {paper.abstract} {paper.venue} {' '.join(paper.fields_of_study)}"
    tags = [
        label for label, pattern in TOPIC_PATTERNS.items() if re.search(pattern, text, re.I)
    ]
    ccf = ccf_rank(paper.venue)
    if ccf:
        tags.append(ccf)
    if paper.source:
        tags.append(f"source:{paper.source}")
    return _dedupe(tags)


def ccf_rank(venue: str) -> str:
    normalized = venue.upper()
    for key, rank in CCF_VENUES.items():
        if key.upper() in normalized:
            return rank
    return ""


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
