import io
import os
import zipfile
from typing import Optional

import asyncpg
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI(title="Kansas LAS File API")

# Public HF dataset repo - no token needed to download from it.
# If you make the repo private, add HF_TOKEN here and pass it as a header below.
HF_REPO_ID = os.environ.get("HF_REPO_ID", "your-username/kansas-las-files")
HF_BASE_URL = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main"


@app.on_event("startup")
async def startup():
    app.state.pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])


@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()


@app.get("/wells/search")
async def search_wells(
    county: Optional[str] = None,
    operator: Optional[str] = None,
    api: Optional[str] = None,
    limit: int = 20,
):
    query = """
        SELECT kgs_id, well_name, county, operator, lease, latitude, longitude,
               start_depth, stop_depth, curves, year_archive
        FROM wells
        WHERE 1=1
    """
    params = []
    if county:
        params.append(county)
        query += f" AND county ILIKE ${len(params)}"
    if operator:
        params.append(f"%{operator}%")
        query += f" AND operator ILIKE ${len(params)}"
    if api:
        params.append(api)
        query += f" AND api_official = ${len(params)}"
    query += f" LIMIT {limit}"

    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    return [dict(r) for r in rows]


@app.get("/wells/{kgs_id}/download")
async def download_well(kgs_id: str):
    async with app.state.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT shard_id, filename_in_shard FROM wells WHERE kgs_id = $1", kgs_id
        )
    if not row or not row["shard_id"]:
        raise HTTPException(status_code=404, detail="no file available for this well")

    shard_url = f"{HF_BASE_URL}/shards/{row['shard_id']}"
    r = requests.get(shard_url, timeout=60)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail="could not fetch shard from storage")

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        try:
            data = zf.read(row["filename_in_shard"])
        except KeyError:
            raise HTTPException(status_code=404, detail="file missing from shard")

    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{row["filename_in_shard"]}"'},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
