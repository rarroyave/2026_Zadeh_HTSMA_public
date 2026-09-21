"""The augmented transformation-temperature model is wired to the right data.

These tests are deliberately structural: they check that the port of the
vendored CatBoost-SMAs pipeline still selects the same records, builds the same
feature matrix, and carries the same hyperparameters. They do not fit a model,
because a single MultiRMSE fit on ~3,100 features takes minutes; the accuracy
of the fitted model is measured by scripts/train_tt_augmented.py itself.
"""

import ast
import sys
from pathlib import Path

import pytest

pytest.importorskip("CBFV")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import train_tt_augmented as T  # noqa: E402


# --------------------------------------------------------------- training data
def test_literature_selection_matches_the_vendored_pipeline():
    """main.py keeps 1,811 of the 4,900 raw records; NOTICE.md records the same."""
    assert len(T.literature_frame()) == 1811


def test_literature_modelling_pool_matches_the_vendored_pipeline():
    """main.py then holds out compositions that occur only once, leaving 1,689."""
    lit = T.to_formula_df(T.literature_frame())
    pool = lit.groupby("formula").filter(lambda g: len(g) > 1)
    assert len(pool) == 1689


def test_campaign_alloys_are_the_transforming_second_cycle_measurements():
    """All 81 transforming alloys survive the ordering filter.

    Before the two transcription errors recorded in data/README.md were fixed,
    two rows had M_f > M_s and were dropped here, leaving 79.
    """
    camp = T.campaign_frame()
    assert len(camp) == 81
    counts = (camp[T.ELEM39] > 0).sum(axis=1).value_counts().to_dict()
    assert counts == {4: 22, 5: 24, 6: 27, 7: 8}


def test_campaign_alloys_carry_the_campaign_homogenization_schedule():
    camp = T.campaign_frame()
    assert (camp["Processing_FinalHT_Temp"] == T.DEFAULT_HT_TEMP).all()
    assert (camp["Processing_FinalHT_Time"] == T.DEFAULT_HT_TIME).all()


def test_campaign_measurements_are_physically_ordered():
    """Mf < Ms, Mf < As, Ms < Af and As < Af, the filter main.py applies."""
    c = T.campaign_frame()
    assert (c.SME_Mf < c.SME_Ms).all()
    assert (c.SME_Mf < c.SME_As).all()
    assert (c.SME_Ms < c.SME_Af).all()
    assert (c.SME_As < c.SME_Af).all()


# ------------------------------------------------------- why augmentation exists
def test_literature_data_contains_no_alloy_of_this_campaigns_complexity():
    """The published training set is ternary and quaternary only."""
    lit = T.literature_frame()
    assert (lit[T.ELEM39] > 0).sum(axis=1).max() == 4


def test_almost_every_campaign_family_is_unseen_in_the_literature_data():
    """`family` is a CatBoost categorical, so an unseen value carries no signal.

    Only one of the campaign's fourteen alloy families appears in the
    literature records; augmentation is what makes the other thirteen known.
    """
    lit_families = set(T.to_formula_df(T.literature_frame()).family)
    camp_families = set(T.to_formula_df(T.campaign_frame()).family)
    assert len(camp_families) == 14
    assert len(camp_families & lit_families) == 1


def test_the_champion_alloys_family_is_known_only_through_the_campaign():
    champion = T.to_formula_df(T.query_frame([{"Ni": 46, "Ti": 28, "Co": 2, "Pd": 2, "Hf": 22}]))
    family = champion.family.iloc[0]
    assert family == "CoHfNiPdTi"
    assert family not in set(T.to_formula_df(T.literature_frame()).family)
    assert family in set(T.to_formula_df(T.campaign_frame()).family)


# ------------------------------------------------------------------- features
def test_features_align_across_literature_campaign_and_query():
    """One CBFV pass over all frames, so a query row cannot drift from training."""
    lit = T.to_formula_df(T.literature_frame())
    pool = lit.groupby("formula").filter(lambda g: len(g) > 1).reset_index(drop=True)
    camp = T.to_formula_df(T.campaign_frame())
    query = T.to_formula_df(T.query_frame([{"Ni": 46, "Ti": 28, "Co": 2, "Pd": 2, "Hf": 22}]))

    X_lit, X_camp, X_q = T.build_features([pool, camp, query])
    assert (len(X_lit), len(X_camp), len(X_q)) == (1689, 81, 1)
    assert list(X_lit.columns) == list(X_camp.columns) == list(X_q.columns)
    assert all(c in X_q.columns for c in T.CAT)
    # CBFV median-imputes; nothing may be left missing, or CatBoost would refuse.
    for frame in (X_lit, X_camp, X_q):
        assert frame.isna().sum().sum() == 0


def test_query_defaults_to_the_campaign_schedule():
    q = T.query_frame([{"Ni": 50, "Ti": 50}])
    assert q["Processing_FinalHT_Temp"].iloc[0] == 950.0
    assert q["Processing_FinalHT_Time"].iloc[0] == 24.0
    # Arc-melted and solution treated only: no thermomechanical processing, and
    # encoded explicitly so CBFV cannot median-impute rolled or extruded values.
    assert q["Processing_HR_Red"].iloc[0] == 0.0
    assert q["Processing_CR_Red"].iloc[0] == 0.0
    assert q["Processing_Extrusion_Area_Reduction(%)"].iloc[0] == 0.0


# --------------------------------------------------------------- drift guards
def test_hyperparameters_still_match_the_vendored_model():
    """If vendored/CatBoost-SMAs/main.py changes, this port must not silently differ."""
    tree = ast.parse((REPO / "vendored" / "CatBoost-SMAs" / "main.py").read_text(encoding="utf-8"))
    vendored = next(
        ast.literal_eval(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "params" for t in node.targets)
    )
    for key in ("learning_rate", "depth", "l2_leaf_reg", "bagging_temperature",
                "loss_function", "eval_metric"):
        assert T.PARAMS[key] == vendored[key], key


def test_reported_accuracy_covers_every_target():
    """Every predicted temperature is quoted with a measured error, never bare."""
    assert set(T.CV_MAE) == set(T.LABELS) == {"Ms", "Mf", "As", "Af"}
    # Recorded from the grouped 5-fold run documented in the module docstring.
    assert all(30.0 < v < 90.0 for v in T.CV_MAE.values())


# ------------------------------------------------------------------ fitted model
def test_fitted_model_recovers_alloys_it_was_trained_on():
    """One real fit, as a guard against the pipeline silently breaking.

    These three alloys are in the training set, so this measures fit quality,
    not predictive accuracy -- the honest out-of-sample numbers are CV_MAE. The
    tolerance is deliberately loose: the point is to catch a pipeline that has
    stopped working (misaligned features, wrong target order, lost categoricals),
    not to pin values that legitimately move with library versions.

    This costs roughly seven minutes, which is why it is the only test here that
    fits anything.
    """
    pytest.importorskip("catboost")
    champion = {"Ni": 46, "Ti": 28, "Co": 2, "Pd": 2, "Hf": 22}
    septenary = {"Ni": 36, "Ti": 23, "Cu": 5, "Co": 2, "Pd": 7, "Hf": 19, "Zr": 8}
    pred, notes = T.predict([champion, septenary])

    assert list(pred.columns) == ["Ms", "Mf", "As", "Af"]
    assert any("1689 literature records" in n and "81 campaign" in n for n in notes)
    # The default schedule must not be reported as an extrapolation.
    assert not any("extrapolation" in n for n in notes)

    measured_champion = {"Ms": 224.9, "Mf": 194.3, "As": 232.8, "Af": 241.4}
    for target, value in measured_champion.items():
        assert abs(pred.iloc[0][target] - value) < 40.0, target

    # Ordering must survive the fit: Mf < Ms < Af and Ms < Af.
    for row in (pred.iloc[0], pred.iloc[1]):
        assert row["Mf"] < row["Ms"] < row["Af"]

    # The septenary alloy transforms below room temperature. The literature-only
    # model predicted +209 C against -70 C measured; getting the sign right is
    # the clearest single sign that the campaign data is actually being used.
    assert pred.iloc[1]["Ms"] < 0.0
