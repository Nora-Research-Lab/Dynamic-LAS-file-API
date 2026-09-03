# Kansas LAS File API — Render deployment

## Files
- `main.py` — the FastAPI app: `/wells/search` and `/wells/{kgs_id}/download`
- `requirements.txt` — dependencies
- `db_load.py` — one-time script to create the `wells` table and load the notebook's CSV output
- `render.yaml` — Render blueprint (optional — lets Render auto-configure the service)

## Setup
1. Create a Postgres database on Render (free tier), copy its connection string.
2. Run the loader once, locally or from Colab, pointed at that database:
   ```
   DATABASE_URL=<your-render-postgres-url> python db_load.py kansas_las_master_index.csv
   ```
3. Push this folder to a GitHub repo.
4. On Render: New → Web Service → connect the repo. It'll pick up `render.yaml` automatically,
   or set manually: build command `pip install -r requirements.txt`, start command
   `uvicorn main:app --host 0.0.0.0 --port $PORT`.
5. Set environment variables on the service:
   - `DATABASE_URL` — same Postgres connection string
   - `HF_REPO_ID` — your Hugging Face dataset repo, e.g. `your-username/kansas-las-files`

## Try it
```
GET /wells/search?county=Haskell
GET /wells/{kgs_id}/download
```

The dataset repo is assumed public, so no HF token is needed on Render itself — only the Colab
notebook needs one (for uploading shards), stored as a Colab secret named `HF_TOKEN`.
