# MedRE Partners website

Static site for medrepartners.com, hosted on DigitalOcean App Platform.

## How it works

- Original Claude Design source pages live in the "MedRE Partners" Claude project (site/ folder); `source/` in this repo is added as sessions permit
- `build.py` converts them into a deployable static site in `dist/` (clean URLs, canonical tags, sitemap, redirects)
- `dist/` is committed to the repo; DigitalOcean serves it directly (no build step on their side)
- `do/app.yaml` defines the DigitalOcean app, including the custom domains
- `.github/workflows/deploy.yml` deploys to DigitalOcean on every push to `main`

## Updating the site

1. Replace or add pages in `source/` (export from Claude Design)
2. If adding a new page, add its filename and slug to `SLUGS` in `build.py`
3. Run `python3 build.py`
4. Commit and push to `main`; the GitHub Action deploys automatically

## URL structure

Slugs are locked per the Metadata Master Sheet and should not change after launch.
Redirect stubs exist for `/for-physicians` and `/resources`.
