# The YEET Terminal

Streamlit starter with a RAMBO dashboard, sourced October 14, 2026 snapshot, batch UW CSV import, contract/event matching, admin event entry and ticker coverage list.

## Launch from GitHub in your browser

1. Keep this repository private if it contains paid research or raw flow. A password on the app does not protect files in a public GitHub repository.
2. Upload the project files and folders to the root of your repository. `app.py` and `requirements.txt` belong at the top level, not inside another YEETterminal2 folder.
3. Go to https://share.streamlit.io and sign in with GitHub.
4. Create an app using `Zeuswasalaker/YEETterminal2`, your repository's default branch, and `app.py` as the entrypoint.
5. In the app's Settings → Secrets, add these with your own passwords:

```toml
ACCESS_PASSWORD = "choose-a-member-password"
ADMIN_PASSWORD = "choose-a-different-admin-password"
```

6. Save and open the app. With ACCESS_PASSWORD configured, every page requires it. Without it, the research dashboard is public. Admin uploads and edits remain disabled until ADMIN_PASSWORD is configured.

## Daily workflow

Open Upload & publish, unlock admin, select all downloaded UW CSVs, and click Import and recalculate. Review matches in RAMBO. Download the publishable snapshot and replace `data/snapshot.json` in GitHub to update the shared site. Uploaded files and edits otherwise exist only in the current Streamlit session. Do not assume server disk or session state is durable.

## Automation included

The GitHub Actions workflow checks known event-source pages twice each weekday (13:17 and 22:17 UTC). It writes changes/fetch failures to `data/source_checks.json`, visible in Event research. It does not discover every company automatically, confirm new dates, scrape UW or invent event/trade interpretations. This is the safe first source-monitoring layer. Confirm new discoveries through admin event entry, then publish the snapshot.

## What is ready

- Dark responsive dashboard and event/contract details with official source links.
- Upload validation, canceled-row removal, exact record deduplication and filter provenance.
- Multi-day events matched only when the contract covers the event's end date.
- Earnings-related events and unconfirmed candidates excluded from matches.
- Manual admin entry for researched events and requested tickers.
- Reader/admin shared-password gates.

## Next integrations

Persistent shared storage will remove the daily snapshot commit. Substack membership verification and Founding Member request delivery are not connected yet. Prestige/PARI/WARI are honest empty states until their real feeds and calculations are supplied. The starter never exposes Prestige thresholds.

## Local development

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files explained

- `app.py`: pages, upload controls and visual HTML/CSS.
- `rambo.py`: CSV normalization and expiry/event matching.
- `data/snapshot.json`: approved research and observed flow.
- `refresh_ir.py`: source-page change monitor.
- `.github/workflows/check-events.yml`: scheduled monitoring.
- `.streamlit/config.toml`: theme.
