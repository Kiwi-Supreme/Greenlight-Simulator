"""Precompute analytical statistics for the Greenlight Simulator dashboard."""
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pandas as pd
import numpy as np
from movie_lib import load_movies, CLASS_NAMES

DATA_DIR = BACKEND_DIR

def generate_statistics():
    print("Loading movies dataset...")
    df = load_movies()
    print(f"Loaded {len(df)} movies.")

    # 1. Highest-earning actors (top 10 by cumulative worldwide box office revenue)
    exp_actors = df.explode("cast_names")
    exp_actors = exp_actors[exp_actors["cast_names"].notna() & (exp_actors["cast_names"] != "")]
    actor_stats = []
    for actor, adf in exp_actors.groupby("cast_names"):
        if len(adf) >= 4:  # meaningful track record (at least 4 movies)
            tot_rev = float(adf["revenue"].sum())
            hits = int((adf["target"] == 2).sum())
            actor_stats.append({
                "actor": str(actor),
                "total_revenue_billions": round(tot_rev / 1_000_000_000, 2),
                "avg_revenue_millions": round(float(adf["revenue"].mean()) / 1_000_000, 1),
                "movies_count": int(len(adf)),
                "hits_count": hits,
                "hit_rate_pct": round((hits / len(adf)) * 100, 1)
            })
    actor_stats.sort(key=lambda x: x["total_revenue_billions"], reverse=True)
    top_actors = actor_stats[:10]

    # 2. Movies that made the most money (top 10 by revenue)
    grossing_movies = df.sort_values("revenue", ascending=False).head(10)
    top_grossing = []
    for _, r in grossing_movies.iterrows():
        top_grossing.append({
            "title": str(r.get("title", "Unknown")),
            "year": int(r["year"]) if pd.notna(r["year"]) else None,
            "revenue": float(r["revenue"]),
            "revenue_millions": round(float(r["revenue"]) / 1_000_000, 1),
            "budget_millions": round(float(r["budget"]) / 1_000_000, 1),
            "roi": round(float(r["roi"]), 2)
        })

    # 3. Which month has the most sales
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    monthly_sales = []
    for m in range(1, 13):
        m_df = df[df["month"] == m]
        tot_rev = float(m_df["revenue"].sum())
        avg_rev = float(m_df["revenue"].mean()) if len(m_df) else 0.0
        monthly_sales.append({
            "month_num": m,
            "month_name": month_names[m - 1],
            "total_revenue_billions": round(tot_rev / 1_000_000_000, 2),
            "avg_revenue_millions": round(avg_rev / 1_000_000, 1),
            "movie_count": int(len(m_df))
        })

    # 4. Which genre has better sales
    exploded_genres = df.explode("genre_list")
    exploded_genres = exploded_genres[exploded_genres["genre_list"].notna() & (exploded_genres["genre_list"] != "")]
    genre_stats = []
    for g, gdf in exploded_genres.groupby("genre_list"):
        if len(gdf) >= 15:
            genre_stats.append({
                "genre": str(g),
                "total_revenue_billions": round(float(gdf["revenue"].sum()) / 1_000_000_000, 2),
                "avg_revenue_millions": round(float(gdf["revenue"].mean()) / 1_000_000, 1),
                "avg_budget_millions": round(float(gdf["budget"].mean()) / 1_000_000, 1),
                "avg_roi": round(float(gdf["roi"].median()), 2),
                "count": int(len(gdf))
            })
    genre_stats.sort(key=lambda x: x["total_revenue_billions"], reverse=True)

    # 5. Which director is leading
    director_stats = []
    for d, ddf in df[df["director"].notna()].groupby("director"):
        if len(ddf) >= 4:
            tot_rev = float(ddf["revenue"].sum())
            hits = int((ddf["target"] == 2).sum())
            director_stats.append({
                "director": str(d),
                "total_revenue_billions": round(tot_rev / 1_000_000_000, 2),
                "avg_revenue_millions": round(float(ddf["revenue"].mean()) / 1_000_000, 1),
                "movies_count": int(len(ddf)),
                "hits_count": hits,
                "hit_rate_pct": round((hits / len(ddf)) * 100, 1)
            })
    director_stats.sort(key=lambda x: x["total_revenue_billions"], reverse=True)
    top_directors = director_stats[:10]

    # 6. Overall distribution & Budget vs Revenue relationship sample
    class_counts = df["target"].value_counts().to_dict()
    outcome_distribution = [
        {"name": CLASS_NAMES[0], "count": int(class_counts.get(0, 0)), "pct": round(int(class_counts.get(0, 0)) / len(df) * 100, 1)},
        {"name": CLASS_NAMES[1], "count": int(class_counts.get(1, 0)), "pct": round(int(class_counts.get(1, 0)) / len(df) * 100, 1)},
        {"name": CLASS_NAMES[2], "count": int(class_counts.get(2, 0)), "pct": round(int(class_counts.get(2, 0)) / len(df) * 100, 1)}
    ]

    sample_df = df.sample(min(250, len(df)), random_state=42)
    budget_vs_revenue = []
    for _, r in sample_df.iterrows():
        budget_vs_revenue.append({
            "title": str(r.get("title", "")),
            "budget_millions": round(float(r["budget"]) / 1_000_000, 1),
            "revenue_millions": round(float(r["revenue"]) / 1_000_000, 1),
            "target": int(r["target"])
        })

    data = {
        "total_movies": int(len(df)),
        "top_actors": top_actors,
        "top_grossing": top_grossing,
        "monthly_sales": monthly_sales,
        "genre_sales": genre_stats,
        "top_directors": top_directors,
        "outcome_distribution": outcome_distribution,
        "budget_vs_revenue": budget_vs_revenue
    }

    out_file = DATA_DIR / "statistics.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Successfully generated {out_file} with top_actors ({out_file.stat().st_size} bytes)")

if __name__ == "__main__":
    generate_statistics()
