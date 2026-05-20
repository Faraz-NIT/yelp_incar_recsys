"""Central configuration for the Yelp in-car restaurant recommender system."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR: Path = Path(__file__).resolve().parents[1]
DATA_DIR: Path = ROOT_DIR / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
MODELS_DIR: Path = ROOT_DIR / "models"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Expected raw Yelp file names
YELP_BUSINESS_JSON = "yelp_academic_dataset_business.json"
YELP_REVIEW_JSON = "yelp_academic_dataset_review.json"
YELP_USER_JSON = "yelp_academic_dataset_user.json"
YELP_TIP_JSON = "yelp_academic_dataset_tip.json"

# Processed parquet outputs
BUSINESS_PARQUET = "businesses.parquet"
REVIEW_PARQUET = "reviews.parquet"
USER_PARQUET = "users.parquet"
INTERACTION_PARQUET = "interactions.parquet"


# ---------------------------------------------------------------------------
# Pipeline settings
# ---------------------------------------------------------------------------
@dataclass
class PipelineConfig:
    """Top-level pipeline parameters.

    These can be overridden from the admin page or the CLI.
    """

    cities: list[str] = field(
        default_factory=lambda: ["Philadelphia", "Tampa", "New Orleans"]
    )
    min_user_reviews: int = 2
    min_business_reviews: int = 3
    review_sample_size: int | None = None  # None = use all that fit filters
    test_size: float = 0.2
    random_state: int = 42

    # Sentiment
    sentiment_blend_alpha: float = 0.7  # weight on star, (1-alpha) on sentiment

    # Matrix factorisation
    mf_n_factors: int = 64
    mf_n_epochs: int = 20
    mf_lr_all: float = 0.005
    mf_reg_all: float = 0.02

    # Content-based filtering
    content_max_features: int = 5000
    content_ngram_range: tuple[int, int] = (1, 2)

    # Hybrid weights
    weight_personalized: float = 0.45
    weight_content: float = 0.20
    weight_popularity: float = 0.15
    weight_distance: float = 0.20

    # Location
    default_radius_km: float = 5.0
    max_radius_km: float = 25.0
    distance_decay_km: float = 5.0  # softplus decay constant

    # Cold start
    cold_start_review_threshold: int = 3


DEFAULT_CONFIG = PipelineConfig()


# ---------------------------------------------------------------------------
# Cuisine taxonomy (for cold-start onboarding)
# ---------------------------------------------------------------------------
CUISINE_OPTIONS: list[str] = [
    "American (New)",
    "American (Traditional)",
    "Italian",
    "Mexican",
    "Japanese",
    "Sushi Bars",
    "Chinese",
    "Thai",
    "Indian",
    "Mediterranean",
    "French",
    "Korean",
    "Vietnamese",
    "Pizza",
    "Burgers",
    "Steakhouses",
    "Seafood",
    "Vegetarian",
    "Vegan",
    "Cafes",
    "Coffee & Tea",
    "Breakfast & Brunch",
    "Bakeries",
    "Desserts",
    "Barbeque",
    "Tex-Mex",
    "Greek",
    "Spanish",
    "Tapas Bars",
    "Ramen",
]

PRICE_LEVELS: dict[str, str] = {
    "1": "$ — Inexpensive",
    "2": "$$ — Moderate",
    "3": "$$$ — Pricey",
    "4": "$$$$ — Ultra High-End",
}

ATTRIBUTE_LABELS: dict[str, str] = {
    "RestaurantsTakeOut": "Takeout",
    "RestaurantsDelivery": "Delivery",
    "RestaurantsReservations": "Reservations",
    "OutdoorSeating": "Outdoor seating",
    "GoodForKids": "Kid friendly",
    "BikeParking": "Bike parking",
    "WheelchairAccessible": "Wheelchair accessible",
    "DogsAllowed": "Dogs allowed",
}

# Model file names inside MODELS_DIR
MODEL_FILES = {
    "popularity": "popularity.pkl",
    "content_based": "content_based.pkl",
    "item_cf": "item_cf.pkl",
    "user_cf": "user_cf.pkl",
    "matrix_fact": "matrix_fact.pkl",
    "metadata": "metadata.json",
}
