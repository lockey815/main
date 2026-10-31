"""Aggregation of per-sample findings into one result + human-readable summary."""
from __future__ import annotations

import logging
import re

import httpx

from .config import Settings

log = logging.getLogger("leuknet.analysis")

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
TEST_NAME = "Blood smear examination for blast cells"


def aggregate(findings: list[dict], s: Settings) -> dict:
    valid = [f for f in findings if f["status"] != "unknown"]
    total = sum(f["blast_count"] for f in valid)
    foreign = sum(f.get("foreign_objects", 0) for f in findings)
    max_p = max((f["max_blast_probability"] for f in valid), default=0.0)

    if not valid:
        result = "unknown"
    elif total > 0:
        result = "blast_detected"
    else:
        result = "normal"

    indication = ""
    if result == "blast_detected" and s.acute_blast_threshold > 0:
        indication = "acute" if total > s.acute_blast_threshold else "chronic"

    return {
        "result": result,
        "indication": indication,
        "sample_size": len(findings),
        "images_analyzed": len(valid),
        "total_blasts": total,
        "foreign_objects": foreign,
        "max_blast_probability": max_p,
    }


def template_summary(agg: dict, s: Settings) -> str:
    n, foreign = agg["images_analyzed"], agg["foreign_objects"]
    skipped = agg["sample_size"] - n
    foreign_txt = (
        "No foreign objects were detected in the sample."
        if foreign == 0
        else f"{foreign} possible foreign object region(s) were flagged and excluded from the blast count."
    )
    skipped_txt = f" {skipped} sample(s) could not be analysed." if skipped else ""

    if agg["result"] == "unknown":
        return "None of the uploaded samples could be analysed. Please upload clear, in-focus blood smear images."
    if agg["result"] == "normal":
        return (
            f"No blast cells were found in {n} analysed sample(s).{skipped_txt} {foreign_txt} "
            "A normal screening result does not exclude disease; correlate clinically."
        )
    if agg["indication"] == "acute":
        verdict = (f"Acute lymphoblastic leukemia is indicated (more than {s.acute_blast_threshold} "
                   "suspected blast regions).")
    elif agg["indication"] == "chronic":
        verdict = (f"Chronic leukemia is indicated (no more than {s.acute_blast_threshold} "
                   "suspected blast regions).")
    else:
        verdict = "A possible leukemic condition is indicated."
    return (
        f"{agg['total_blasts']} suspected blast region(s) were found in {n} analysed sample(s).{skipped_txt} "
        f"{verdict} {foreign_txt} This is a screening aid; confirm with microscopy and clinical review."
    )


def _mistral_call(payload: dict, key: str, timeout: float) -> dict:
    r = httpx.post(MISTRAL_URL, json=payload, timeout=timeout,
                   headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    r.raise_for_status()
    return r.json()


def make_summary(agg: dict, s: Settings) -> tuple[str, str]:
    """-> (summary_text, source) where source is 'mistral' or 'template'.
    Only aggregate numbers are sent to Mistral - never names, contacts or images."""
    fallback = template_summary(agg, s)
    if not s.mistral_api_key or agg["result"] == "unknown":
        return fallback, "template"

    facts = {
        "samples_uploaded": agg["sample_size"],
        "samples_analysed": agg["images_analyzed"],
        "suspected_blast_regions": agg["total_blasts"],
        "foreign_object_regions": agg["foreign_objects"],
        "screening_result": {"normal": "no blasts found", "blast_detected": "blasts detected"}[agg["result"]],
        "indication": agg["indication"] or "none",
    }
    payload = {
        "model": s.mistral_model,
        "temperature": 0.2,
        "max_tokens": 220,
        "messages": [
            {"role": "system", "content": (
                "You write short, plain-language summaries of AI blood-smear screening results for laboratory "
                "staff. Use ONLY the facts provided and do not invent numbers. Do not give a definitive diagnosis. "
                "Say the result is a screening aid that must be reviewed by a qualified pathologist or hematologist. "
                "Write 2-3 sentences, no headings, no lists.")},
            {"role": "user", "content": f"Facts: {facts}"},
        ],
    }
    try:
        data = _mistral_call(payload, s.mistral_api_key, s.mistral_timeout)
        text = data["choices"][0]["message"]["content"].strip()
        allowed = {str(v) for v in facts.values() if isinstance(v, int)}
        numbers = set(re.findall(r"\d+", text))
        if not text or len(text) > 1200 or not numbers <= allowed:
            log.warning("Mistral summary rejected (empty/too long/unexpected numbers); using template")
            return fallback, "template"
        return text, "mistral"
    except Exception as exc:  # network error, quota, bad key ... never block saving a report
        log.warning("Mistral summary failed (%s); using template", type(exc).__name__)
        return fallback, "template"
