# Forecast Data

Submit your space weather forecasts here.

## How to submit

1. Create a JSON file named `YYYY-MM-DD_your-name.json` (e.g., `2026-08-20_jane-smith.json`)
2. Use the template format (see `_template.json`)
3. Submit a pull request or push directly if you have write access

## File format

\`\`\`json
{
  "predictor_name": "Your Name",
  "predictor_type": "human",
  "target_date": "2026-08-20",
  "kp_forecast": 5.5,
  "flare_forecast": "M",
  "aurora_lat_forecast": 55,
  "storm_timing_forecast": "2026-08-20T18:00:00Z",
  "notes": "Your methodology or reasoning"
}
\`\`\`

## Rules

- One file per predictor per date
- Forecasts must be submitted before the target date begins (00:00 UTC)
- `predictor_type` must be `"human"` or `"ai"`
- All fields are optional but more fields = more comprehensive scoring
