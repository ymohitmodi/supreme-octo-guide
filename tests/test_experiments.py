"""The self-run benchmarks must produce real, deterministic, sensible numbers."""
from __future__ import annotations

from darkfactory.experiments import (
    auc,
    run_experiment,
    run_injection_detection,
    run_membership_inference,
    run_robustness,
    tpr_at_fpr,
)


def test_experiments_are_deterministic():
    for topic in ("prompt-injection", "adversarial-examples", "membership-inference"):
        a = run_experiment(topic, seed=7)
        b = run_experiment(topic, seed=7)
        assert a.table_rows == b.table_rows
        assert a.metrics == b.metrics


def test_metric_helpers():
    # A perfectly separable score set gives AUC 1.0; identical distributions ~0.5.
    assert auc([1.0, 0.9, 0.8], [0.1, 0.2, 0.3]) == 1.0
    assert 0.4 <= auc([0.5, 0.5], [0.5, 0.5]) <= 0.6
    assert tpr_at_fpr([1.0, 0.9], [0.1, 0.2], 0.0) == 1.0


def test_injection_generalization_gap_is_real_and_positive():
    r = run_injection_detection(seed=1337)
    rows = {row[0]: row for row in r.table_rows}
    id_f1 = float(rows["In-distribution"][-1])
    oo_f1 = float(rows["Adaptive (unseen)"][-1])
    # In-distribution should be strong and the adaptive split strictly worse —
    # the whole point: fixed test sets overstate robustness.
    assert id_f1 >= 0.9
    assert oo_f1 < id_f1
    assert "gap" in r.finding.lower()


def test_adversarial_training_helps_at_high_epsilon():
    r = run_robustness(seed=1337)
    # rows: [eps, std_acc, adv_acc]; clean accuracy is healthy, and at the largest
    # epsilon the adversarially trained model is at least as robust as standard.
    clean_std = float(r.table_rows[0][1])
    assert clean_std >= 0.8
    worst_std = float(r.table_rows[-1][1])
    worst_adv = float(r.table_rows[-1][2])
    assert worst_adv >= worst_std


def test_membership_leakage_decreases_with_data():
    r = run_membership_inference(seed=1337)
    aucs = [float(row[1]) for row in r.table_rows]  # AUC column, ordered by train size
    # Small training set leaks (AUC well above chance); large set approaches chance.
    assert aucs[0] > 0.65
    assert aucs[-1] < aucs[0]
    assert aucs[-1] <= 0.6
