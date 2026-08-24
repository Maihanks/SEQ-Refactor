"""Detector precision/recall/F1 study (Working Brief Phase 2c §4): separates
detector quality from scheduler quality, so a reviewer cannot argue the
scheduling results ride on detection errors.

Uses the generator's own planted ground truth as the reference. This is a
genuine, independent check, not a circular one, because of the same
independence property Working Brief Phase 2 §1.1 established for the
generator itself: the native detector (``detect/native.py``) never reads a
subject's manifest, so comparing what it finds in the real ``.java`` source
against what the manifest says was planted is a real precision/recall
measurement, not the detector grading its own homework.
"""

from __future__ import annotations

from dataclasses import dataclass

from seqrefactor import ingest
from seqrefactor.datasets import DATASETS_DIR, list_subjects, load_manifest
from seqrefactor.detect import native as detect_native


@dataclass
class DetectorQualityResult:
    subject: str
    ground_truth_count: int
    detected_count: int
    true_positives: int
    precision: float
    recall: float
    f1: float


def _ground_truth_pairs(subject: str) -> set[tuple[str, str]]:
    manifest = load_manifest(subject)
    return {(s["category"], s["loc"][0]) for s in manifest["smells"]}


def _detected_pairs(subject: str) -> set[tuple[str, str]] | None:
    """None for a subject with no real Java source (e.g. the hand-written
    graph-only fixtures billing_cycle_v1/notification_mixed_v1) -- precision/
    recall against a detector that never ran is not a meaningful number."""
    module = ingest.load(DATASETS_DIR / subject)
    if not module.source_files:
        return None
    smells = detect_native.detect(module)
    return {(s.category, s.loc[0]) for s in smells}


def compute_detector_quality(subject: str) -> DetectorQualityResult | None:
    ground_truth = _ground_truth_pairs(subject)
    detected = _detected_pairs(subject)
    if detected is None:
        return None

    true_positives = len(ground_truth & detected)
    precision = true_positives / len(detected) if detected else 0.0
    recall = true_positives / len(ground_truth) if ground_truth else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return DetectorQualityResult(
        subject=subject,
        ground_truth_count=len(ground_truth),
        detected_count=len(detected),
        true_positives=true_positives,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
    )


def run_study(subjects: list[str] | None = None) -> list[DetectorQualityResult]:
    """Compute detector precision/recall/F1 for every subject with real
    source (``subjects`` defaults to the whole synthetic corpus,
    ``seqrefactor.datasets.list_subjects()``); subjects with no compilable
    source are silently excluded (see ``_detected_pairs``), not scored zero.
    """
    subjects = subjects if subjects is not None else list_subjects()
    results = []
    for subject in subjects:
        result = compute_detector_quality(subject)
        if result is not None:
            results.append(result)
    return results
