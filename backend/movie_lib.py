"""Shared helpers: load the movie data, build pre-release features, make predictions.

Target: ROI class = revenue / budget
    0 = Flop (< 1x), 1 = Modest (1x - 3x), 2 = Hit (>= 3x)

Only information known BEFORE release is used as a feature. Director / cast /
studio "track record" is computed from earlier movies only, so no future info leaks in.
"""
import ast
from pathlib import Path

import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATASETS_DIR = PROJECT_ROOT / "datasets" if (PROJECT_ROOT / "datasets").exists() else BACKEND_DIR
DATA_DIR = BACKEND_DIR
CLASS_NAMES = ["Flop (<1x)", "Modest (1-3x)", "Hit (>=3x)"]
SMOOTH_K = 3  # shrinks track records of people with few movies toward the average


def roi_class(roi):
    return 0 if roi < 1 else (1 if roi < 3 else 2)


def _names(text, limit=None):
    try:
        items = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return []
    names = [i["name"] for i in items if isinstance(i, dict) and "name" in i]
    return names[:limit] if limit else names


def _director(text):
    try:
        for p in ast.literal_eval(text):
            if p.get("job") == "Director":
                return p["name"]
    except (ValueError, SyntaxError):
        pass
    return None


def load_movies():
    m = pd.read_csv(DATASETS_DIR / "movies_metadata.csv", low_memory=False)
    m = m[pd.to_numeric(m["id"], errors="coerce").notna()].copy()  # a few malformed rows
    m["id"] = m["id"].astype(int)
    for c in ["budget", "revenue", "runtime", "popularity", "vote_count", "vote_average"]:
        m[c] = pd.to_numeric(m[c], errors="coerce")
    m["release_date"] = pd.to_datetime(m["release_date"], errors="coerce")
    # Zeros in budget/revenue mean "unknown" in this dataset, so keep only known, non-trivial values.
    m = m[(m["status"] == "Released") & (m["budget"] >= 10_000) & (m["revenue"] >= 10_000)]
    m = m[m["release_date"].notna() & m["runtime"].notna()].drop_duplicates("id")

    credits = pd.read_csv(DATASETS_DIR / "credits.csv")
    credits = credits[credits["id"].isin(m["id"])].drop_duplicates("id")
    credits["director"] = credits["crew"].map(_director)
    credits["cast_names"] = credits["cast"].map(lambda t: _names(t, 3))
    m = m.merge(credits[["id", "director", "cast_names"]], on="id", how="inner")

    m["genre_list"] = m["genres"].map(_names)
    m["companies"] = m["production_companies"].map(lambda t: _names(t, 3))
    m["roi"] = m["revenue"] / m["budget"]
    m["target"] = m["roi"].map(roi_class)
    m["year"] = m["release_date"].dt.year
    m["month"] = m["release_date"].dt.month
    m["log_budget"] = np.log10(m["budget"])
    m["is_english"] = (m["original_language"] == "en").astype(int)
    m["in_collection"] = m["belongs_to_collection"].notna().astype(int)
    return m.sort_values("release_date").reset_index(drop=True)


class History:
    """Running (sum, count) of log-ROI for every director / actor / studio seen so far."""

    def __init__(self):
        self.people = {}
        self.overall = [0.0, 0]

    def prior(self):
        return self.overall[0] / self.overall[1] if self.overall[1] else 0.0

    def score(self, key):
        s, n = self.people[key] if key in self.people else (0.0, 0)
        return (s + SMOOTH_K * self.prior()) / (n + SMOOTH_K), n

    def features(self, director, cast, companies):
        d_score, d_n = self.score(("dir", director)) if director else (self.prior(), 0)
        out = {"director_score": d_score, "director_n": d_n}
        for tag, keys in (("cast", [("cast", c) for c in cast]), ("company", [("co", c) for c in companies])):
            res = [self.score(k) for k in keys] or [(self.prior(), 0)]
            out[f"{tag}_score"] = float(np.mean([r[0] for r in res]))
            out[f"{tag}_n"] = float(np.mean([r[1] for r in res]))
        return out

    def update(self, director, cast, companies, roi):
        y = float(np.clip(np.log(roi), -3, 3))
        keys = ([("dir", director)] if director else []) + [("cast", c) for c in cast] + [("co", c) for c in companies]
        for k in keys:
            entry = self.people.setdefault(k, [0.0, 0])
            entry[0] += y
            entry[1] += 1
        self.overall[0] += y
        self.overall[1] += 1


def build_dataset():
    """Returns the feature table and the final History (used by the app)."""
    m = load_movies()
    genres = sorted({g for gl in m["genre_list"] for g in gl})
    hist = History()
    rows = [None] * len(m)
    for _, day in m.groupby("release_date", sort=True):  # same-day releases can't see each other
        for i, r in day.iterrows():
            rows[i] = hist.features(r["director"], r["cast_names"], r["companies"])
        for i, r in day.iterrows():
            hist.update(r["director"], r["cast_names"], r["companies"], r["roi"])
    m = pd.concat([m, pd.DataFrame(rows)], axis=1)
    for g in genres:
        m[f"genre_{g}"] = m["genre_list"].map(lambda gl, g=g: int(g in gl))
    return m, genres, hist


BASE_FEATURES = ["log_budget", "runtime", "month", "year", "is_english", "in_collection",
                 "director_score", "director_n", "cast_score", "cast_n", "company_score", "company_n"]


def feature_columns(genres):
    return BASE_FEATURES + [f"genre_{g}" for g in genres]


def make_row(inp, genres, hist):
    """Build one model-input row from user choices (used by the Streamlit app)."""
    row = {
        "log_budget": np.log10(inp["budget"]), "runtime": inp["runtime"], "month": inp["month"],
        "year": inp["year"], "is_english": int(inp["english"]), "in_collection": int(inp["sequel"]),
    }
    row.update(hist.features(inp.get("director"), inp.get("cast", []), inp.get("companies", [])))
    for g in genres:
        row[f"genre_{g}"] = int(g in inp["genres"])
    return pd.DataFrame([row])[feature_columns(genres)]
