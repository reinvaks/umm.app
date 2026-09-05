# Nord Pool UMM Dashboard

Streamlit dashboard for current Nord Pool REMIT Urgent Market Messages.

## Architecture

1. Streamlit first reads `https://ummapi.nordpoolgroup.com/messages` directly.
2. If the direct call fails, the app automatically reads `data/umm.json`.
3. GitHub Actions refreshes that snapshot every 15 minutes.
4. A failed/empty fetch never overwrites the last successful snapshot.

No ENTSO-E token is required for Nord Pool UMM reading.

## Deploy

1. Push these files to a GitHub repository.
2. In GitHub: **Settings → Actions → General → Workflow permissions → Read and write permissions**.
3. Run **Actions → Update Nord Pool UMM snapshot → Run workflow** once.
4. Confirm that `data/umm.json` was committed.
5. In Streamlit Community Cloud create an app from the repository; entry point: `umm.app.py`.

## Local test

```bash
pip install -r requirements.txt
python fetch_snapshot.py
streamlit run umm.app.py
```

## Diagnostics

The Streamlit UI shows live HTTP status/error details under **Andmeallika diagnostika**. This is intentional: network/API failures must not be swallowed silently.
