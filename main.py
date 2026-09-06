import os
import traceback
from typing import Optional

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Kansas Well Index API")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__},
    )


@app.on_event("startup")
async def startup():
    db_url = os.environ["DATABASE_URL"].strip().strip('"').strip("'")
    if not db_url.startswith(("postgres://", "postgresql://")):
        raise RuntimeError(
            f"DATABASE_URL doesn't look like a Postgres connection string "
            f"(starts with {db_url[:15]!r}) - check for a stray character in the Render env var"
        )
    app.state.pool = await asyncpg.create_pool(db_url)


@app.on_event("shutdown")
async def shutdown():
    await app.state.pool.close()


@app.get("/wells/search")
async def search_wells(
    operator: Optional[str] = None,
    api: Optional[str] = None,
    limit: int = 20,
):
    query = """
        SELECT kgs_id, operator, lease, api, latitude, longitude, location,
               elevation, depth_start, depth_stop, url
        FROM wells
        WHERE 1=1
    """
    params = []
    if operator:
        params.append(f"%{operator}%")
        query += f" AND operator ILIKE ${len(params)}"
    if api:
        params.append(api)
        query += f" AND api = ${len(params)}"
    query += f" LIMIT {limit}"

    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    return [dict(r) for r in rows]


@app.get("/health")
async def health():
    return {"status": "ok"}
