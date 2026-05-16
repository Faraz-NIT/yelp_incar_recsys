# 🚗 In-Car Restaurant Recommender

A GPS-aware, sentiment-enriched, cold-start-aware hybrid recommender system
for in-car infotainment, built on the **Yelp Open Dataset**.

Pick a driver, drop a pin, get a ranked Top-N of restaurants — each with a
generated rationale and a transparent score breakdown.

> Final project for the *Recommender Systems* course (MSc Data Science & AI
> Strategy, emlyon business school × McGill University, 2026).

---

## Why "in-car"?

Modern infotainment systems (BMW, Mercedes MBUX, Tesla, Android Auto) need
to suggest where to eat *while you're driving*. That makes the problem
different from a desktop "find me a restaurant" tool in three ways:

1. **Distance matters as much as taste** — a 5-star place 25 km away is
   useless when you're hungry now.
2. **Cold start is the norm** — most drivers have no profile on the
   infotainment system; a working onboarding flow is mandatory.
3. **Explanations matter** — a one-line *"why"* per recommendation is the
   difference between trusting the system and ignoring it.

This project addresses all three.

---

## Architecture at a glance

```
                    ┌─────────────────────────────────────────────┐
                    │  Yelp Open Dataset (business / review /     │
                    │  user JSON-L, ~5 GB total)                  │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │  src/preprocessing.py                       │
                    │  ── streaming JSON-L reader                 │
                    │  ── restaurant-only filter                  │
                    │  ── k-core sparse pruning                   │
                    │  ── parquet outputs                         │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │  src/sentiment.py  (VADER)                  │
                    │  effective_rating = α·star + (1-α)·sentiment│
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
   ┌───────────────────────────────────┴─────────────────────────────────┐
   │                          src/recommenders/                          │
   │                                                                     │
   │   popularity ─┐                                                     │
   │   content    ─┤                                                     │
   │   item_cf    ─┼──► hybrid (late fusion)  ─► personalised + content  │
   │   user_cf    ─┤                            + popularity + distance  │
   │   matrix_fact─┘                                                     │
   └──────────────────────────────────┬──────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────────┐
                    │  app/  (Streamlit, 4 pages)                 │
                    │  Discover · Map · Admin · Analytics         │
                    └─────────────────────────────────────────────┘
```

---

## Quick start

You have three paths. **Use Path A first** — it gets you to a working demo
in under two minutes with no Yelp download.

### Path A — synthetic data (fastest)

```bash
# 1. Set up the env
conda env create -f environment.yml
conda activate yelp-incar-recsys

# 2. Generate ~600 users, 300 restaurants of synthetic Yelp-format data
python scripts/make_sample_data.py

# 3. Run the full pipeline (preprocess → sentiment → train → evaluate)
python scripts/run_pipeline.py

# 4. Launch the app
streamlit run app/app.py
```

Open <http://localhost:8501>. The synthetic data is designed to give the
recommenders *real* signal — reviews use rating-conditional vocabulary so
VADER picks up genuine sentiment patterns.

### Path B — real Yelp data

1. Download the dataset from <https://www.yelp.com/dataset>.
2. Unzip it and drop these three files into `data/raw/`:
   - `yelp_academic_dataset_business.json`
   - `yelp_academic_dataset_review.json`
   - `yelp_academic_dataset_user.json`
3. Open the Streamlit app (`streamlit run app/app.py`) and go to the
   **Admin** page. Pick a city (Philadelphia, Tampa, and New Orleans
   are the most represented in the dataset), adjust thresholds, and
   click **Run selected stages**. The progress bar shows live status.

Or, headless via CLI:

```bash
python scripts/run_pipeline.py \
    --cities Philadelphia \
    --min-user-reviews 5 \
    --min-business-reviews 10
streamlit run app/app.py
```

### Path C — Docker

```bash
# Build & run (single-stage build per the project guide)
make docker-up
# or:
docker compose up -d
```

App is at <http://localhost:8501>. `data/` and `models/` are mounted from
the host so artefacts survive container restarts.

To enable Claude-generated explanations, export an API key first:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
docker compose up -d
```

---

## The five recommenders

Each implements the same `BaseRecommender` interface (`fit`, `recommend`,
`score_pairs`). All return scores normalised to `[0, 1]` so the hybrid can
combine them without per-model calibration.

| Model | Algorithm | Cold-start? | Used as |
|---|---|---|---|
| **Popularity** | Bayesian-smoothed mean rating × log-volume | ✅ (no user needed) | Baseline + hybrid component |
| **Content-based** | TF-IDF over categories+attributes+price, cosine sim | ✅ (with stated cuisines) | Hybrid component, similar-item lookups |
| **Item-CF** | Mean-centered cosine k-NN on items | ❌ | Evaluated alongside MF |
| **User-CF** | k-NN on users | ❌ | Evaluated alongside MF |
| **Matrix factorisation** | Surprise SVD on sentiment-blended ratings (TruncatedSVD fallback) | partial | Primary personalised signal in the hybrid |
| **Hybrid** | Late-fusion: `w_p·pers + w_c·content + w_o·pop + w_d·dist` | ✅ | **What the app actually uses** |

### Why sentiment is blended *before* training

We compute a VADER compound score per review and map it linearly to
`[1, 5]`. Then:

```
effective_rating = α · star  +  (1 - α) · sentiment_star
```

with `α = 0.7` by default (tunable in the admin UI). This effective rating
is what the matrix factoriser learns from. The intuition: a 4-star review
whose text reads "*pretty good but service was rough, food cold, won't
return*" gets discounted; a 4-star review reading "*absolutely loved
everything, best in town*" gets a small boost. The signal-to-noise ratio
on ratings goes up.

### How distance enters

For each candidate restaurant we compute the haversine distance from the
user's GPS. The radius slider is a **hard filter** (anything outside is
dropped), but inside the radius we still rank by a soft distance score:

```
distance_score = exp(-distance_km / 5.0)
```

So an 800 m restaurant scores 0.85 and a 5 km restaurant scores 0.37 —
distance still influences ranking inside the radius, it doesn't just gate
the candidate set.

### Cold start

Three regimes, all detected automatically:

- **`new`** (no ratings on file) — drop the personalised signal entirely,
  re-weight onto content + popularity. The user's stated cuisine
  preferences from the onboarding wizard become a Rocchio-style content
  profile that overrides the user-history-derived content profile.
- **`light`** (1–2 ratings) — keep CF in the mix at 60 % strength, boost
  content and popularity.
- **`established`** (3+ ratings) — full hybrid weights.

The active weights and regime are shown in the Discover page's
"Under the hood" expander, so you can see the rebalancing in real time.

---

## The Streamlit app

Four pages in the sidebar:

### 1. 🍽️ Discover

The main user flow:

1. Pick a returning user (selectbox of the 50 most-active users in the
   dataset) **or** choose "New user (cold start)" to trigger onboarding.
2. Confirm GPS — via the browser's geolocation API, by picking a city
   centroid from the dropdown, or by typing coordinates.
3. Tweak the sidebar filters: radius, minimum stars, price levels,
   must-have attributes (takeout / delivery / outdoor / kid-friendly),
   Top-N.
4. Optionally tick "Use Claude for the 'why' text" to swap the template
   rationale for a one-line Claude-generated one (needs
   `ANTHROPIC_API_KEY`).

### 2. 🗺️ Map View

The same recommendations rendered as a folium map: your location plus a
radius circle, pins coloured by hybrid score (orange = top pick, yellow
= strong, green = solid). Click any pin for details.

### 3. 🛠️ Admin

**The pipeline control panel.** A form lets you set:

- Cities to include
- Min reviews per user / per restaurant
- Optional cap on review count (for laptops with limited RAM)
- Sentiment blend α
- MF latent factors and epochs
- Hybrid component weights

Tick which stages to run (preprocess / sentiment / train / evaluate) and
hit ▶ — a live progress bar reports `[stage XX%] message...` updates from
the pipeline. When evaluation runs, the resulting metrics table appears
inline. A danger zone at the bottom lets you delete artifacts to start
clean.

### 4. 📊 Analytics

- Model comparison table (RMSE / MAE / Precision@10 / Recall@10 / NDCG@10)
  loaded from `models/evaluation_results.csv`
- Sentiment distribution histogram + sentiment-vs-star agreement table
- Top-20 cuisine frequencies
- Ratings-per-user distribution + matrix sparsity
- Geographic spread of all restaurants on a base map

---

## Evaluation

The pipeline holds out one rating per user (when they have ≥4 ratings) for
testing. Five metrics are reported per model:

- **RMSE** and **MAE** (predicted vs actual rating, on the star scale)
- **Precision@10**, **Recall@10**, **NDCG@10** — relevance defined as a
  held-out rating ≥ 4.0

The hybrid is evaluated alongside its components. Expect the hybrid to
lead on NDCG@10 because it gets the popularity prior for free for cold
items and the personalised score for warm items.

Saved to `models/evaluation_results.csv` after every run.

---

## Project structure

```
yelp_incar_recsys/
├── app/
│   ├── app.py                          # Landing page
│   ├── components/
│   │   ├── cards.py                    # Recommendation card renderer
│   │   ├── cold_start.py               # Onboarding wizard
│   │   ├── filters.py                  # Sidebar filters
│   │   ├── location.py                 # GPS / city / coord picker
│   │   └── styles.py                   # Dark automotive theme CSS
│   └── pages/
│       ├── 1_🍽️_Discover.py
│       ├── 2_🗺️_Map_View.py
│       ├── 3_🛠️_Admin.py
│       └── 4_📊_Analytics.py
├── data/
│   ├── raw/                            # Yelp JSON drop zone (gitignored)
│   ├── processed/                      # Parquet outputs (gitignored)
│   └── notebooks/
│       └── eda.ipynb                   # Exploratory notebook
├── models/                             # Pickled fitted recommenders
├── scripts/
│   ├── make_sample_data.py             # Synthetic Yelp-format generator
│   └── run_pipeline.py                 # Headless CLI for the full pipeline
├── src/
│   ├── config.py                       # PipelineConfig + constants
│   ├── preprocessing.py                # JSON-L → parquet
│   ├── sentiment.py                    # VADER + rating blend
│   ├── geo.py                          # Haversine + city centroids
│   ├── cold_start.py                   # Regime detection + weight rebalancing
│   ├── evaluation.py                   # Train/test split + ranking metrics
│   ├── llm_explain.py                  # Optional Claude explanations
│   ├── pipeline.py                     # End-to-end orchestrator
│   ├── utils.py                        # Logging, pickling, timing
│   └── recommenders/
│       ├── base.py
│       ├── popularity.py
│       ├── content_based.py
│       ├── collaborative.py            # Item-CF + User-CF
│       ├── matrix_factorization.py     # Surprise SVD + fallback
│       └── hybrid.py                   # Late-fusion combiner
├── tests/
│   └── test_recommenders.py            # Smoke tests on synthetic data
├── Dockerfile
├── docker-compose.yml
├── environment.yml
├── requirements.txt
├── Makefile
├── LICENSE
└── README.md
```

---

## Team & MVP success criteria

This was built as a five-person final project. Suggested role split:

- **Project manager / Report lead** — report, slides, presentation, github hygiene
- **Data engineer** — `preprocessing.py`, EDA notebook, parquet pipeline
- **ML dev 1** — popularity, content, user-CF
- **ML dev 2** — item-CF, matrix factorisation, hybrid, evaluation
- **Frontend / app dev** — Streamlit pages, CSS, map view, filters

Success criteria each gate must hit before declaring the phase done:

| Phase | Definition of done |
|---|---|
| Data | k-core pruned parquet files load in < 5 s, no nulls in `user_id`/`business_id` |
| Sentiment | `effective_rating` distribution differs measurably from raw stars |
| Models | All five recommenders fit and persist without error on synthetic + real data |
| Hybrid | NDCG@10 strictly above the popularity baseline on the held-out test set |
| App | Cold-start user can complete a Top-N flow end-to-end with no manual edits |

---

## Bonus features (per the project guide)

- **+2 Docker support** — single-stage `Dockerfile` + `docker-compose.yml`,
  one unified environment for training and inference.
- **+4 LLM augmentation** — Claude Haiku generates a one-sentence,
  signal-aware rationale per recommendation (uses the matched cuisines,
  star rating, distance, and a short snippet of top-rated review text).
  Falls back to a deterministic template when no API key is present, so
  the system always works.

---

## Yelp dataset terms

Use of the Yelp Open Dataset is governed by Yelp's
[Terms of Use](https://www.yelp.com/dataset). It is licensed for academic
use only and is **not** redistributed by this repository — you must
download it yourself.

---

## License

[MIT](LICENSE) — code only. The Yelp dataset retains its original terms.
