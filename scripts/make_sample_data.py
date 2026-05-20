"""Generate a small synthetic dataset that looks like the Yelp dataset.

The real Yelp Open Dataset is ~5GB compressed. Downloading and processing it
to get a working demo takes time and disk space, so this script writes a
self-contained synthetic dataset in the Yelp JSON-lines format under
``data/raw/``. The rest of the pipeline runs unmodified on it.

Run:
    python scripts/make_sample_data.py --n-users 800 --n-businesses 400
"""

from __future__ import annotations

import argparse
import json
import random
import string
import sys
from datetime import date, timedelta
from pathlib import Path

# Make ``src`` importable when running this file directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from src.config import (RAW_DIR, YELP_BUSINESS_JSON,  # noqa: E402
                        YELP_REVIEW_JSON, YELP_TIP_JSON, YELP_USER_JSON)
from src.geo import CITY_CENTROIDS  # noqa: E402

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------
CUISINES = [
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
    "Barbeque",
    "Tex-Mex",
    "Greek",
    "Spanish",
    "Ramen",
    "Ethiopian",
    "Lebanese",
]

NAME_PREFIXES = [
    "The",
    "Casa",
    "Mama's",
    "Luigi's",
    "Sakura",
    "Tokyo",
    "Bella",
    "El",
    "La",
    "Le",
    "Royal",
    "Golden",
    "Blue",
    "Red",
    "Green",
    "Urban",
    "Rustic",
    "Modern",
    "Old",
]
NAME_SUFFIXES = [
    "Kitchen",
    "Bistro",
    "Café",
    "Diner",
    "Grill",
    "House",
    "Garden",
    "Tavern",
    "Eatery",
    "Bar",
    "Cantina",
    "Bowl",
    "Co.",
    "& Co.",
    "Shop",
    "Counter",
    "Table",
    "Room",
]

POS_PHRASES = [
    "absolutely loved the food",
    "best meal in months",
    "service was warm and attentive",
    "atmosphere is so cozy",
    "portions are generous",
    "would definitely come back",
    "fresh ingredients, full of flavour",
    "hidden gem of the neighbourhood",
]
NEG_PHRASES = [
    "the wait was way too long",
    "food was cold when it arrived",
    "service felt rushed and inattentive",
    "prices are too high for what you get",
    "noisy and cramped inside",
    "would not recommend",
    "the menu was disappointing",
    "not as good as the reviews suggested",
]
NEUTRAL_PHRASES = [
    "decent spot for a quick bite",
    "nothing special but not bad either",
    "you get what you pay for",
    "average experience overall",
    "okay if you're in the area",
    "menu has some hits and some misses",
]


def _rand_id(length: int = 22) -> str:
    return "".join(
        random.choices(string.ascii_letters + string.digits + "_-", k=length)
    )


def _rand_name() -> str:
    return f"{random.choice(NAME_PREFIXES)} {random.choice(NAME_SUFFIXES)}"


def _rand_address(city: str) -> str:
    return f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Cedar', 'Market', 'Broad', 'Walnut'])} St, {city}"


def _rand_date(start: date = date(2017, 1, 1), end: date = date(2024, 12, 31)) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()


def _rand_review_text(target_stars: int) -> str:
    """Generate review text whose tone roughly matches the star rating."""
    if target_stars >= 4:
        pool, k = POS_PHRASES, 3
    elif target_stars <= 2:
        pool, k = NEG_PHRASES, 3
    else:
        pool, k = NEUTRAL_PHRASES, 2
    return ". ".join(random.sample(pool, k=min(k, len(pool)))) + "."


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------
def generate_businesses(
    n: int, cities: list[str], rng: np.random.Generator
) -> list[dict]:
    businesses = []
    for _ in range(n):
        city = random.choice(cities)
        centroid = CITY_CENTROIDS.get(city, (39.9526, -75.1652))
        lat = centroid[0] + rng.normal(0, 0.05)
        lon = centroid[1] + rng.normal(0, 0.05)
        n_cuisines = rng.integers(1, 4)
        cuisines = random.sample(CUISINES, k=int(n_cuisines))
        n_reviews = int(np.clip(rng.lognormal(mean=3.5, sigma=1.0), 5, 800))
        # Base quality (latent star tendency)
        true_star = float(np.clip(rng.normal(3.6, 0.7), 1.5, 5.0))
        rounded = round(true_star * 2) / 2  # rounded to half-stars
        biz = {
            "business_id": _rand_id(),
            "name": _rand_name(),
            "address": _rand_address(city),
            "city": city,
            "state": "CA",
            "postal_code": f"{rng.integers(10000, 99999)}",
            "latitude": float(lat),
            "longitude": float(lon),
            "stars": float(rounded),
            "review_count": n_reviews,
            "is_open": 1,
            "attributes": {
                "RestaurantsTakeOut": str(bool(rng.binomial(1, 0.85))),
                "RestaurantsDelivery": str(bool(rng.binomial(1, 0.55))),
                "RestaurantsReservations": str(bool(rng.binomial(1, 0.40))),
                "OutdoorSeating": str(bool(rng.binomial(1, 0.35))),
                "GoodForKids": str(bool(rng.binomial(1, 0.65))),
                "WheelchairAccessible": str(bool(rng.binomial(1, 0.70))),
                "RestaurantsPriceRange2": str(int(rng.integers(1, 5))),
            },
            "categories": ", ".join(["Restaurants"] + cuisines),
            "hours": {
                "Monday": "11:00-22:00",
                "Tuesday": "11:00-22:00",
                "Wednesday": "11:00-22:00",
                "Thursday": "11:00-22:00",
                "Friday": "11:00-23:00",
                "Saturday": "10:00-23:00",
                "Sunday": "10:00-21:00",
            },
            "_true_star": true_star,  # private, removed before writing
        }
        businesses.append(biz)
    return businesses


def generate_users(n: int, rng: np.random.Generator) -> list[dict]:
    users = []
    for _ in range(n):
        nr = int(np.clip(rng.lognormal(2.0, 1.0), 3, 200))
        users.append(
            {
                "user_id": _rand_id(),
                "name": "".join(random.choices(string.ascii_letters, k=6)),
                "review_count": nr,
                "yelping_since": _rand_date(),
                "friends": [],
                "useful": int(rng.integers(0, 50)),
                "funny": int(rng.integers(0, 30)),
                "cool": int(rng.integers(0, 30)),
                "fans": int(rng.integers(0, 20)),
                "elite": [],
                "average_stars": float(np.clip(rng.normal(3.7, 0.4), 1.0, 5.0)),
                "_taste_bias": float(rng.normal(0, 0.5)),  # private latent factor
                "_preferred_cuisines": random.sample(
                    CUISINES, k=int(rng.integers(2, 5))
                ),
            }
        )
    return users


def generate_reviews(
    users: list[dict],
    businesses: list[dict],
    rng: np.random.Generator,
    avg_per_user: float = 12.0,
) -> list[dict]:
    reviews: list[dict] = []
    for user in users:
        n = max(1, int(rng.poisson(avg_per_user)))
        # Bias: 70% of reviews go to businesses matching user's preferred cuisines
        prefs = set(user["_preferred_cuisines"])
        prefer = [
            b for b in businesses if prefs.intersection(b["categories"].split(", "))
        ]
        other = [b for b in businesses if b not in prefer]
        sampled = []
        n_prefer = min(int(n * 0.7), len(prefer))
        n_other = min(n - n_prefer, len(other))
        if prefer:
            sampled.extend(random.sample(prefer, k=n_prefer))
        if other:
            sampled.extend(random.sample(other, k=n_other))
        for biz in sampled:
            # Star = clip(true_star + user_bias + noise)
            star = float(
                np.clip(
                    biz["_true_star"] + user["_taste_bias"] + rng.normal(0, 0.5),
                    1,
                    5,
                )
            )
            star_int = int(round(star))
            text = _rand_review_text(star_int)
            reviews.append(
                {
                    "review_id": _rand_id(),
                    "user_id": user["user_id"],
                    "business_id": biz["business_id"],
                    "stars": star_int,
                    "date": _rand_date(),
                    "text": text,
                    "useful": int(rng.integers(0, 10)),
                    "funny": int(rng.integers(0, 5)),
                    "cool": int(rng.integers(0, 5)),
                }
            )
    return reviews


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------
def write_jsonl(rows: list[dict], path: Path, strip_private: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            r = {
                k: v for k, v in r.items() if not (strip_private and k.startswith("_"))
            }
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {len(rows):>7,} rows to {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-users", type=int, default=600)
    parser.add_argument("--n-businesses", type=int, default=300)
    parser.add_argument("--avg-per-user", type=float, default=12.0)
    parser.add_argument(
        "--cities",
        nargs="+",
        default=["Philadelphia", "Tampa", "New Orleans"],
        help="Subset of cities for which to generate restaurants",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    rng = np.random.default_rng(args.seed)

    print(f"Generating {args.n_businesses} businesses across {args.cities} ...")
    businesses = generate_businesses(args.n_businesses, args.cities, rng)

    print(f"Generating {args.n_users} users ...")
    users = generate_users(args.n_users, rng)

    print("Generating reviews (this may take a moment) ...")
    reviews = generate_reviews(users, businesses, rng, avg_per_user=args.avg_per_user)

    # Tips: subset of users leaving short text tips
    tips = []
    for r in random.sample(reviews, k=min(200, len(reviews))):
        tips.append(
            {
                "text": r["text"][:80],
                "date": r["date"],
                "compliment_count": int(rng.integers(0, 5)),
                "business_id": r["business_id"],
                "user_id": r["user_id"],
            }
        )

    write_jsonl(businesses, RAW_DIR / YELP_BUSINESS_JSON)
    write_jsonl(users, RAW_DIR / YELP_USER_JSON)
    write_jsonl(reviews, RAW_DIR / YELP_REVIEW_JSON)
    write_jsonl(tips, RAW_DIR / YELP_TIP_JSON)

    print("\nDone. You can now run the pipeline:")
    print("    python scripts/run_pipeline.py --cities", " ".join(args.cities))


if __name__ == "__main__":
    main()
