from scripts.run_eval import run_phase1_precision_eval


def test_phase1_top3_precision_meets_target():
    precision = run_phase1_precision_eval(top_k=3)
    assert precision >= 0.85
