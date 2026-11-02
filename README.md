# Greenlight Simulator

A machine learning application and interactive analytics dashboard that predicts commercial movie outcomes (**Flop**, **Modest**, or **Hit**) before theatrical release using strictly pre-release signals.

---

## Project Structure

```text
Predictive/
│
├── backend/
│   ├── __init__.py
│   ├── compute_stats.py
│   ├── model.joblib
│   ├── movie_lib.py
│   ├── server.py
│   ├── statistics.json
│   └── train.py
│
├── datasets/
│   ├── credits.csv
│   └── movies_metadata.csv
│
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
├── outputs/
│   ├── confusion_matrix.png
│   ├── feature_importance.png
│   └── results.csv
│
├── .env
├── .gitignore
├── README.md
└── run.py
```

---

## Quick Start

### 1. Prerequisites

Ensure Python 3.10 or higher is installed.

Install the required dependencies:

```bash
pip install flask pandas numpy scikit-learn joblib matplotlib
```

### 2. Launch the Web Application

From the project root directory, run:

```bash
python run.py
```

Open your browser and navigate to:

**http://127.0.0.1:5000**

---

## Core Capabilities

### 1. Interactive Movie Simulator

- **Budget Range Slider:** Select an estimated production budget from $0.1M to $400M, synchronized with a numerical input.
- **Release Month:** Select a release month from January to December.
- **Release Year & Distribution Scope:** Specify the projected release year and distribution scope (Global release, Released in a few states, or Other locations).
- **Creative Team & Studio:** Search historical track records for directors, lead actors, and production studios.
- **Lead Cast Selection:** Select up to three actors.
- **Real-Time Predictions:** View probability breakdowns for Flop (<1x), Modest (1–3x), and Hit (>=3x).
- **Release Timing Analysis:** Explore a 12-month release timing sensitivity curve.
- **OMDb Integration:** Search for real-world movies by title and year to automatically populate simulator inputs.

### 2. Industry Analytics Dashboard

Accessible through the **Statistics** button in the top-right header.

- **Highest-Earning Actors:** Top 10 actors ranked by cumulative worldwide box office, average gross per film, and hit rate.
- **Highest-Grossing Movies:** Explore the all-time highest worldwide box office earners.
- **Monthly Box Office Performance:** Analyze cumulative box office performance across all 12 months.
- **Genre Analysis:** Compare total box office earnings and median Return on Investment (ROI) across genres.
- **Leading Directors:** Explore filmmakers with at least four catalog titles, ranked by cumulative revenue and hit consistency.
- **Outcome Distribution:** Examine the distribution of Flop, Modest, and Hit movie outcomes.

---

## Machine Learning Methodology

The project uses a **Random Forest Classifier** to predict commercial movie outcomes.

Key methodological considerations:

1. **No Information Leakage:** Only information available before theatrical release is used as a feature. Post-release metrics such as `vote_count`, `vote_average`, and `popularity` are excluded.

2. **Temporal Train-Test Split:** Movies released on or before 2011 are used for training, while movies released after 2011 are used for testing.

3. **Past-Only Track Records:** Historical performance for directors, actors, and studios is calculated using only movies released before the target movie's release date. Bayesian smoothing is applied toward the prior mean.

4. **Class Imbalance Handling:** Uses the `balanced_subsample` class-weighting strategy in the Random Forest classifier to handle imbalanced outcome classes.

---

## Optional Pipelines

### Retrain the Machine Learning Model

To re-evaluate the algorithms and update the trained model:

```bash
python backend/train.py
```

This generates evaluation metrics and plots in the `outputs/` folder.

### Recompute Industry Statistics

To recalculate analytical rankings and metrics:

```bash
python backend/compute_stats.py
```

This updates `backend/statistics.json`.

---

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend development and machine learning |
| Flask | REST API and application server |
| Pandas | Data processing and analysis |
| NumPy | Numerical computations |
| Scikit-learn | Machine learning and evaluation |
| HTML & CSS | Frontend structure and styling |
| JavaScript | Interactive application functionality |
| Chart.js | Data visualization |
| Joblib | Model serialization |
| OMDb API | Movie information and autofill |

---

## Configuration

### OMDb API Key

To enable live movie autofill, create a `.env` file in the project root and add your API key:

```env
OMDB_API_KEY=your_key_here
```

---

## Project Objective

Greenlight Simulator aims to demonstrate how machine learning and historical movie-industry data can be used to estimate commercial movie outcomes before theatrical release.

By combining predictive modelling with interactive analytics, the application helps users understand factors influencing box office performance and explore trends across the film industry.
