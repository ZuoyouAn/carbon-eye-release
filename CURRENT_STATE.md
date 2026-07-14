# Carbon Eye Current State

Generated before the final data-upgrade changes.

## Already Present

- Vue route `/carbon-eye`, `CarbonEyeView.vue`, ECharts, and a `/projects` entry.
- FastAPI read-only Carbon Eye endpoints for overview, trends, weather, city carbon background, warnings, daily cases, methodology, realtime AQI, legacy park estimate, CDCI, industry profile, and governance explanation.
- Existing JSON data for 152 monthly city-background air-quality records, 12 months of 2024 weather, 20 city carbon-background records, 13 warnings, and historical daily cases.
- A local data-build script and a third-party realtime AQI fallback module.
- Render and Netlify configuration files.

## Needs Repair Or Upgrade

- The current CDCI uses the superseded 0.4/0.3/0.3 design and backfills annual carbon context into monthly records. It must be replaced by the requested PRI/EAI/CEI design and an explicitly experimental CDCI with sensitivity analysis.
- The current park-carbon output is based on a legacy economic allocation. It must be replaced by the supplied official electricity and location-based purchased-electricity proxy data.
- Air-quality records need explicit partial-month, relative-anomaly, and absolute-risk fields; legacy source-attribution names need cautious, non-causal wording.
- The frontend needs the supplied official six-site monitoring snapshot, long-term weather, descriptive correlation, electricity-intensity, data-quality, source, and sensitivity views.
- The backend needs standalone `/healthz`, environment-driven CORS, new static-data endpoints, and JSON-missing 503 messages with a regeneration command.
- The realtime module should prefer the formal AQICN API only when `AQICN_TOKEN` is supplied at runtime; HTML scraping must not be the production data path.

## Data Package To Import

- Official electricity, economic-activity, factor, monitoring-site, short-term snapshot, industry-profile, source-registry, and weather-schema files are available in the supplied bundle.
- The package also includes weather download, weather-air analysis, and validation scripts, plus official reference PDFs.

## Potential Conflicts And Safety Notes

- The Git repository has no commit yet and contains a staged local npm cache and deployment/IDE state. These must be unstaged and ignored before the first public commit; local files remain untouched.
- Existing non-Carbon Eye application modules, authentication, articles, messages, and database code are out of scope and will not be refactored.
- City-scale air-quality and city CO2 background must remain clearly separated from the park-scale short-term monitoring snapshot and purchased-electricity proxy.
- The supplied 2020-2022 electricity gap will remain a visible gap. No interpolation or reverse calculation will be introduced.
