# Space Weather Forecast Benchmark

An open, zero-cost benchmark comparing **human vs AI** space weather forecasting accuracy. Public datasets, transparent scoring, and a live leaderboard.

## What is this?

This repository maintains a public benchmark for space weather forecasting. Anyone can submit forecasts (human or AI), and they are automatically scored against observed NOAA data.

## How it works

1. **Submit a forecast** — Add a JSON file to `data/forecasts/` with your prediction
2. **Automatic scoring** — A GitHub Action runs daily, fetching observed data from NOAA SWPC and scoring all forecasts
3. **Live leaderboard** — Results are published to the leaderboard and GitHub Pages

## Submit a Forecast

Create a file at `data/forecasts/YYYY-MM-DD_<your-name>.json`:

\`\`\`json
{
  "predictor_name": "Your Name or Model Name",
  "predictor_type": "human",
  "target_date": "2026-08-20",
  "kp_forecast": 5.5,
  "flare_forecast": "M",
  "aurora_lat_forecast": 55,
  "storm_timing_forecast": "2026-08-20T18:00:00Z",
  "notes": "Optional reasoning or methodology"
}
\`\`\`

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `predictor_name` | string | Your name or your model's name |
| `predictor_type` | string | `"human"` or `"ai"` |
| `target_date` | string | The date you're forecasting for (YYYY-MM-DD) |
| `kp_forecast` | number | Predicted max Kp index (0-9) |
| `flare_forecast` | string | Predicted max flare class (A/B/C/M/X) |
| `aurora_lat_forecast` | number | Predicted lowest aurora-visible latitude (degrees) |
| `storm_timing_forecast` | string | Predicted storm peak time (ISO 8601) |
| `notes` | string | Optional methodology or reasoning |

## Scoring Methodology

### Kp Index (0-9)
- **MAE**: Absolute error from observed value
- **Score**: 100 - (MAE × 10), clamped to 0-100
- **Direction**: Over, under, or correct estimate

### Flare Class (A/B/C/M/X)
- **Exact match**: 100 points
- **1 class off**: 80 points
- **2 classes off**: 50 points
- **3+ classes off**: 0 points

### Storm Timing
- **Hours off**: Absolute difference from observed peak
- **Score**: 100 - (hours × 5), clamped to 0-100

### Aurora Latitude
- **Degree error**: Absolute difference from observed
- **Score**: 100 - (degrees × 2), clamped to 0-100

### Overall
- Average of all category scores
- Brier score for probabilistic forecasts

## Data Sources

All observed data comes from [NOAA SWPC](https://www.swpc.noaa.gov/):
- [Planetary K-index](https://services.swpc.noaa.gov/json/planetary_k_index_1m.json)
- [GOES X-ray Flux](https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json)
- [ACE Solar Wind](https://services.swpc.noaa.gov/products/ace/ace_swepam_1m.json)

## Cost

**Free** — all data from public government APIs, scoring runs on GitHub Actions.

## License

MIT — the benchmark datasets and scoring code are open source. Forecast submissions remain the property of their respective authors.

## About

Built by [Flarient](https://flarient.com) — the space weather intelligence platform. Part of the [Flarient Constellation](https://github.com/flarientglobal/flarient-constellation).
