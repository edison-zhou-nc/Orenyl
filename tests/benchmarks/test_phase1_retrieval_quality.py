from run_eval import run_phase1_precision_eval


def test_phase1_top5_precision_meets_target():
    precision = run_phase1_precision_eval()
    assert precision >= 0.85
