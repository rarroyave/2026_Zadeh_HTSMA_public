"""Hyperparameters in the vendored model code match Table B1 of the manuscript."""

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Table B1, transformation-temperature row (values as used in the code).
TABLE_B1_TT = {
    "learning_rate": 0.2092,
    "depth": 6,
    "l2_leaf_reg": 0.05992,
    "loss_function": "MultiRMSE",
    "eval_metric": "MultiRMSE",
}


def _module(path):
    return ast.parse(path.read_text(encoding="utf-8"))


def test_catboost_smas_hyperparameters_match_table_b1():
    tree = _module(REPO / "vendored" / "CatBoost-SMAs" / "main.py")
    params = next(
        ast.literal_eval(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "params" for t in node.targets)
    )
    for key, value in TABLE_B1_TT.items():
        assert params[key] == value, key


def test_catboost_smas_split_is_80_20_with_fixed_seed():
    tree = _module(REPO / "vendored" / "CatBoost-SMAs" / "main.py")
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "train_test_split"
    ]
    assert len(calls) == 1
    kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in calls[0].keywords}
    assert kwargs == {"test_size": 0.2, "random_state": 42}
