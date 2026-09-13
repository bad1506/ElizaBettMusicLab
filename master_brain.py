from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import math

ENGINE_VERSION = "6.3"

@dataclass
class BrainDecision:
    action: str
    title: str
    reason: str
    evidence: str
    confidence: float
    severity: str
    gain_db: float
    time_ranges: list[dict[str, float]]
    risk: str
    apply: bool


def _f(v, d=0.0):
    try: return float(v)
    except (TypeError, ValueError): return d


def _severity(v):
    v = _f(v)
    if v >= .78: return "high"
    if v >= .52: return "medium"
    return "low"


def _median(values, default=0.0):
    vals = sorted(_f(x) for x in values if x is not None)
    if not vals: return default
    n=len(vals); m=n//2
    return vals[m] if n%2 else (vals[m-1]+vals[m])/2


def _spectral_evidence(intel: dict[str, Any], key: str, high=True):
    segs = intel.get("spectral", {}).get("segments", [])
    vals=[]
    for s in segs:
        bands=s.get("bands", s.get("band_energy_percent", {}))
        if key in bands: vals.append(_f(bands[key]))
    if not vals: return 0.0
    return _median(vals)


def build_brain(analysis: dict[str, Any]) -> dict[str, Any]:
    """Convert observations into conservative, explainable mastering actions."""
    decisions=[]
    base=analysis.get("decisions", [])
    intel=analysis.get("intelligence", {}) or {}

    # Existing decision engine remains the primary DSP authority.
    for d in base:
        conf=_f(d.get("confidence"), .5)
        sev=_f(d.get("severity"), 0)
        gain=_f(d.get("suggested_gain_db"), 0)
        priority=_f(d.get("priority"), 0)
        if conf < .55 and priority < .5:
            apply=False
        else:
            apply=True
        risk="moderate"
        if abs(gain) <= 1.0: risk="low"
        if abs(gain) > 2.0: risk="high"
        decisions.append(asdict(BrainDecision(
            action=d.get("action", "unknown"), title=d.get("title", d.get("label", "Correction")),
            reason=_reason(d), evidence=f"{d.get('occurrences', 0)} affected segments; context: {d.get('musical_context','unknown')}",
            confidence=round(conf,3), severity=_severity(sev), gain_db=round(gain,2),
            time_ranges=d.get("time_ranges", []), risk=risk, apply=apply)))

    # Intelligence findings that should never silently become EQ commands.
    observational=[]
    for finding in intel.get("findings", []):
        action=finding.get("action", "review")
        if action in {x["action"] for x in decisions}: continue
        observational.append({
            "action": action, "title": finding.get("title", "Audio finding"),
            "reason": finding.get("reason", "Observed by Audio Intelligence."),
            "evidence": finding.get("band", "audio"),
            "confidence": .62 if finding.get("severity")=="medium" else .55,
            "severity": finding.get("severity", "low"), "apply": False,
            "risk": "review", "gain_db": 0.0, "time_ranges": []
        })

    high=sum(1 for d in decisions if d["severity"]=="high")
    medium=sum(1 for d in decisions if d["severity"]=="medium")
    return {
        "version": ENGINE_VERSION,
        "status": "ready" if decisions or observational else "clean",
        "decisions": decisions,
        "observations": observational,
        "summary": {
            "action_count": len(decisions), "observation_count": len(observational),
            "high": high, "medium": medium,
            "auto_apply_count": sum(1 for d in decisions if d["apply"]),
        },
        "policy": {
            "principle": "correct only with evidence; observations do not automatically become DSP commands",
            "rollback": "preserve original when no candidate passes QC",
            "reference": "reference guides target shape but never overrides safety gates",
        },
    }


def _reason(d: dict[str, Any]) -> str:
    p=d.get("problem", "")
    mapping={
      "relative_excess_sub":"Sub energy is elevated relative to the track profile.",
      "relative_excess_bass":"Bass energy is elevated relative to the track profile.",
      "relative_mud":"Low-mid energy is elevated and may reduce separation/clarity.",
      "relative_harshness":"Presence energy is elevated and may increase listening fatigue.",
      "relative_low_air":"Air-band energy is relatively low; only a restrained shelf is considered.",
    }
    return mapping.get(p, "A relative spectral deviation was detected by the Decision Engine.")


def compare_intelligence(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Summarize whether the master reduced targeted pressure without claiming causality."""
    def vals(obj, key):
        return [_f(s.get("bands", s.get("band_energy_percent", {})).get(key)) for s in obj.get("spectral", {}).get("segments", [])]
    keys=["sub_20_60","bass_60_150","low_mid_150_500","presence_2000_6000","air_12000_20000"]
    delta={}
    for k in keys:
        b=_median(vals(before,k),0); a=_median(vals(after,k),0)
        delta[k]=round(a-b,5)
    return {"spectral_median_delta": delta, "finding_count_before": len(before.get("findings", [])),
            "finding_count_after": len(after.get("findings", []))}
