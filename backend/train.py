"""Train and evaluate the Greenlight Simulator. Run:  python train.py"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from movie_lib import CLASS_NAMES, DATA_DIR, build_dataset, feature_columns

PROJECT_ROOT = DATA_DIR.parent
OUT = PROJECT_ROOT / "outputs"
OUT.mkdir(exist_ok=True)
SPLIT_YEAR = 2011  # train on movies up to this year, test on later ones


def new_rf():
    return RandomForestClassifier(n_estimators=500, min_samples_leaf=3, class_weight="balanced_subsample",
                                  random_state=42, n_jobs=-1)


def scores(model, Xtr, ytr, Xte, yte):
    pred = model.fit(Xtr, ytr).predict(Xte)
    return accuracy_score(yte, pred), f1_score(yte, pred, average="macro"), pred


def main():
    df, genres, hist = build_dataset()
    cols = feature_columns(genres)
    train, test = df[df.year <= SPLIT_YEAR], df[df.year > SPLIT_YEAR]
    ytr, yte = train["target"], test["target"]
    print(f"{len(df)} movies | train {len(train)} (<= {SPLIT_YEAR}) | test {len(test)} (> {SPLIT_YEAR})")
    print("class share:", dict(zip(CLASS_NAMES, df["target"].value_counts(normalize=True).sort_index().round(2))))

    results = []
    for name, model in [
        ("Baseline (most common class)", DummyClassifier(strategy="most_frequent")),
        ("Logistic Regression", make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))),
        ("Random Forest", new_rf()),
    ]:
        acc, f1, pred = scores(model, train[cols], ytr, test[cols], yte)
        results.append((name, acc, f1))
        if name == "Random Forest":
            rf, rf_pred = model, pred

    # Leakage demo: post-release signals make the model look much better than it really is at greenlight time.
    leaky_cols = cols + ["vote_count", "vote_average", "popularity"]
    acc, f1, _ = scores(new_rf(), train[leaky_cols].fillna(0), ytr, test[leaky_cols].fillna(0), yte)
    results.append(("RF + post-release votes (LEAKY)", acc, f1))

    table = pd.DataFrame(results, columns=["model", "accuracy", "macro_F1"]).round(3)
    print("\n", table.to_string(index=False))
    table.to_csv(OUT / "results.csv", index=False)

    ConfusionMatrixDisplay.from_predictions(yte, rf_pred, display_labels=CLASS_NAMES, cmap="Blues", colorbar=False)
    plt.title("Random Forest - test set (movies after %d)" % SPLIT_YEAR)
    plt.tight_layout()
    plt.savefig(OUT / "confusion_matrix.png", dpi=150)
    plt.close()

    imp = permutation_importance(rf, test[cols], yte, scoring="f1_macro", n_repeats=10, random_state=42, n_jobs=-1)
    top = pd.Series(imp.importances_mean, index=cols).sort_values().tail(12)
    top.plot.barh(figsize=(7, 5), color="#3b6ea5")
    plt.xlabel("Drop in macro-F1 when feature is shuffled")
    plt.title("What drives the prediction?")
    plt.tight_layout()
    plt.savefig(OUT / "feature_importance.png", dpi=150)
    plt.close()
    print("\nTop features:", list(top.index[::-1][:6]))

    # Final model for the app: refit on all movies.
    final = new_rf().fit(df[cols], df["target"])
    joblib.dump({"model": final, "genres": genres, "hist": hist,
                 "directors": sorted([k[1] for k, v in hist.people.items() if k[0] == "dir"], key=lambda n: -hist.people[("dir", n)][1]),
                 "actors": sorted([k[1] for k, v in hist.people.items() if k[0] == "cast"], key=lambda n: -hist.people[("cast", n)][1]),
                 "companies": sorted([k[1] for k, v in hist.people.items() if k[0] == "co"], key=lambda n: -hist.people[("co", n)][1])},
                DATA_DIR / "model.joblib")
    print("Saved model.joblib and outputs/")


if __name__ == "__main__":
    main()
