#!/usr/bin/env python3
"""
Space Weather Forecast Benchmark — Scoring Engine
Evaluates forecast accuracy for both human and AI predictors.

Scoring methodology:
- Kp forecasts: scored by absolute error and direction (over/under estimate)
- Storm timing: scored by temporal error (hours off from actual peak)
- Storm severity: scored by G-scale accuracy
- Aurora latitude: scored by degree error
- Overall: Brier score for probabilistic forecasts, MAE for point forecasts

All forecasts are scored against NOAA SWPC observed data.
"""

import os
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

NOAA_KP_URL = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
NOAA_XRAY_URL = "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json"
NOAA_SOLAR_WIND_URL = "https://services.swpc.noaa.gov/products/ace/ace_swepam_1m.json"

REPO_DIR = Path(os.environ.get("GITHUB_WORKSPACE", "."))


def log(msg):
    print(f"[benchmark] {msg}", flush=True)


# ── Fetch observed data from NOAA ──────────────────────────────────────────
def fetch_observed_kp(start_date, end_date):
    """Fetch observed Kp values for a date range."""
    try:
        resp = requests.get(NOAA_KP_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Filter by date range
        observed = []
        for entry in data:
            time = entry.get("time_tag", "")
            if time:
                entry_date = time[:10]
                if start_date <= entry_date <= end_date:
                    observed.append({
                        "time": time,
                        "kp": float(entry.get("kp", 0)),
                    })
        return observed
    except Exception as e:
        log(f"  Kp fetch failed: {e}")
    return []


def fetch_observed_flare(start_date, end_date):
    """Fetch the maximum X-ray flare class for a date range."""
    try:
        resp = requests.get(NOAA_XRAY_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        daily_max = {}
        for entry in data:
            time = entry.get("time_tag", "")
            flux = entry.get("flux", 0)
            if time and flux:
                entry_date = time[:10]
                if start_date <= entry_date <= end_date:
                    flux_val = float(flux)
                    if entry_date not in daily_max or flux_val > daily_max[entry_date]:
                        daily_max[entry_date] = flux_val

        # Convert flux to class
        result = {}
        for date, flux in daily_max.items():
            if flux >= 1e-4:
                result[date] = "X"
            elif flux >= 1e-5:
                result[date] = "M"
            elif flux >= 1e-6:
                result[date] = "C"
            elif flux >= 1e-7:
                result[date] = "B"
            else:
                result[date] = "A"
        return result
    except Exception as e:
        log(f"  Flare fetch failed: {e}")
    return {}


# ── Scoring functions ─────────────────────────────────────────────────────
def score_kp_forecast(forecast_kp, observed_kp):
    """
    Score a Kp forecast against the observed value.
    Returns: {mae, direction, score}
    - MAE: absolute error (0-9, lower is better)
    - Direction: "over", "under", "correct"
    - Score: 100 - (mae * 10), clamped to 0-100
    """
    if forecast_kp is None or observed_kp is None:
        return None
    mae = abs(forecast_kp - observed_kp)
    if mae < 0.5:
        direction = "correct"
    elif forecast_kp > observed_kp:
        direction = "over"
    else:
        direction = "under"
    score = max(0, 100 - (mae * 10))
    return {"mae": round(mae, 2), "direction": direction, "score": round(score, 1)}


def score_flare_forecast(forecast_class, observed_class):
    """
    Score a flare class forecast.
    Returns: {correct, score}
    - Correct: True if forecast matches observed class
    - Score: 100 if exact, 80 if adjacent, 50 if 2 classes off, 0 otherwise
    """
    order = {"A": 0, "B": 1, "C": 2, "M": 3, "X": 4}
    f = order.get(forecast_class, 0)
    o = order.get(observed_class, 0)
    diff = abs(f - o)
    if diff == 0:
        return {"correct": True, "score": 100}
    elif diff == 1:
        return {"correct": False, "score": 80}
    elif diff == 2:
        return {"correct": False, "score": 50}
    else:
        return {"correct": False, "score": 0}


def score_storm_timing(forecast_peak_time, observed_peak_time):
    """
    Score storm timing accuracy.
    Returns: {hours_off, score}
    - Hours off: absolute difference in hours
    - Score: 100 - (hours_off * 5), clamped to 0-100
    """
    if not forecast_peak_time or not observed_peak_time:
        return None
    try:
        f = datetime.fromisoformat(forecast_peak_time.replace("Z", "+00:00"))
        o = datetime.fromisoformat(observed_peak_time.replace("Z", "+00:00"))
        hours_off = abs((f - o).total_seconds() / 3600)
        score = max(0, 100 - (hours_off * 5))
        return {"hours_off": round(hours_off, 1), "score": round(score, 1)}
    except:
        return None


def score_aurora_latitude(forecast_lat, observed_lat):
    """
    Score aurora latitude forecast.
    Returns: {degree_error, score}
    - Degree error: absolute difference in degrees
    - Score: 100 - (degree_error * 2), clamped to 0-100
    """
    if forecast_lat is None or observed_lat is None:
        return None
    degree_error = abs(forecast_lat - observed_lat)
    score = max(0, 100 - (degree_error * 2))
    return {"degree_error": round(degree_error, 1), "score": round(score, 1)}


# ── Brier score for probabilistic forecasts ───────────────────────────────
def brier_score(forecast_prob, observed_outcome):
    """
    Calculate Brier score for a probabilistic forecast.
    forecast_prob: 0-1 probability
    observed_outcome: 0 or 1 (did the event happen?)
    Returns: 0 (perfect) to 1 (worst)
    """
    return (forecast_prob - observed_outcome) ** 2


# ── Main scoring pipeline ────────────────────────────────────────────────
def load_forecasts():
    """Load all forecast submissions from the data directory."""
    forecasts = []
    data_dir = REPO_DIR / "data" / "forecasts"
    if data_dir.exists():
        for f in data_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    forecasts.append(json.load(fh))
            except:
                pass
    return forecasts


def score_all_forecasts():
    """Score all forecasts against observed data and update the leaderboard."""
    log("Loading forecasts...")
    forecasts = load_forecasts()
    log(f"  Found {len(forecasts)} forecast submissions")

    if not forecasts:
        log("  No forecasts to score")
        return

    # Determine date range from forecasts
    dates = []
    for fc in forecasts:
        d = fc.get("target_date")
        if d:
            dates.append(d)
    if not dates:
        log("  No valid target dates found")
        return

    start_date = min(dates)
    end_date = max(dates)
    log(f"  Date range: {start_date} to {end_date}")

    # Fetch observed data
    log("Fetching observed data from NOAA...")
    observed_kp = fetch_observed_kp(start_date, end_date)
    observed_flare = fetch_observed_flare(start_date, end_date)

    # Group observed Kp by date and find daily max
    daily_kp_max = {}
    for entry in observed_kp:
        d = entry["time"][:10]
        if d not in daily_kp_max or entry["kp"] > daily_kp_max[d]:
            daily_kp_max[d] = entry["kp"]

    log(f"  Observed Kp for {len(daily_kp_max)} days")
    log(f"  Observed flare classes for {len(observed_flare)} days")

    # Score each forecast
    results = []
    for fc in forecasts:
        predictor = fc.get("predictor_name", "Unknown")
        predictor_type = fc.get("predictor_type", "human")  # human or ai
        target_date = fc.get("target_date")

        result = {
            "predictor_name": predictor,
            "predictor_type": predictor_type,
            "target_date": target_date,
            "scores": {},
        }

        # Score Kp forecast
        if "kp_forecast" in fc:
            obs_kp = daily_kp_max.get(target_date)
            kp_score = score_kp_forecast(fc["kp_forecast"], obs_kp)
            if kp_score:
                result["scores"]["kp"] = kp_score

        # Score flare forecast
        if "flare_forecast" in fc:
            obs_flare = observed_flare.get(target_date)
            flare_score = score_flare_forecast(fc["flare_forecast"], obs_flare)
            if flare_score:
                result["scores"]["flare"] = flare_score

        # Score aurora latitude
        if "aurora_lat_forecast" in fc:
            # We don't have observed aurora latitude easily, skip for now
            pass

        results.append(result)

    # Calculate aggregate scores per predictor
    leaderboard = {}
    for r in results:
        name = r["predictor_name"]
        ptype = r["predictor_type"]
        if name not in leaderboard:
            leaderboard[name] = {
                "name": name,
                "type": ptype,
                "total_score": 0,
                "count": 0,
                "scores": {"kp": [], "flare": []},
            }
        for category, s in r["scores"].items():
            if "score" in s:
                leaderboard[name]["total_score"] += s["score"]
                leaderboard[name]["count"] += 1
                leaderboard[name]["scores"].setdefault(category, []).append(s["score"])

    # Calculate averages
    for name, entry in leaderboard.items():
        if entry["count"] > 0:
            entry["average_score"] = round(entry["total_score"] / entry["count"], 1)
        for cat, scores in entry["scores"].items():
            if scores:
                entry[f"avg_{cat}"] = round(sum(scores) / len(scores), 1)

    # Sort by average score
    sorted_leaderboard = sorted(leaderboard.values(), key=lambda x: x.get("average_score", 0), reverse=True)

    # Save results
    results_dir = REPO_DIR / "data" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(results_dir / "latest_scores.json", "w") as f:
        json.dump({"results": results, "scored_at": datetime.now(timezone.utc).isoformat()}, f, indent=2)

    with open(results_dir / "leaderboard.json", "w") as f:
        json.dump({
            "leaderboard": sorted_leaderboard,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_forecasts": len(forecasts),
            "date_range": {"start": start_date, "end": end_date},
        }, f, indent=2)

    log(f"  Scored {len(results)} forecasts")
    log(f"  Leaderboard: {len(sorted_leaderboard)} predictors")
    for i, entry in enumerate(sorted_leaderboard[:5]):
        log(f"    {i+1}. {entry['name']} ({entry['type']}): {entry.get('average_score', 0)} avg")

    # Write GitHub Actions step summary (if running in CI)
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file and sorted_leaderboard:
        with open(summary_file, "a") as sf:
            sf.write("## Space Weather Forecast Benchmark

")
            sf.write("### Latest Leaderboard

")
            sf.write("| Rank | Predictor | Type | Avg Score | Forecasts |
")
            sf.write("|------|-----------|------|-----------|----------|
")
            for i, entry in enumerate(sorted_leaderboard[:10]):
                sf.write(f"| {i+1} | {entry['name']} | {entry['type']} | {entry.get('average_score', 0)} | {entry['count']} |
")
        log("  Step summary written")


def main():
    log("=== Space Weather Forecast Benchmark ===")
    score_all_forecasts()
    log("Done")


if __name__ == "__main__":
    main()
