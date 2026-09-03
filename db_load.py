"""
One-time loader: creates the `wells` table and loads kansas_las_master_index.csv
(produced by the Colab notebook) into Postgres.

Usage:
    DATABASE_URL=postgres://... python db_load.py kansas_las_master_index.csv
"""
import asyncio
import os
import sys

import asyncpg
import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS wells (
    kgs_id TEXT PRIMARY KEY,
    api_las TEXT,
    well_name TEXT,
    company TEXT,
    county TEXT,
    start_depth DOUBLE PRECISION,
    stop_depth DOUBLE PRECISION,
    curves TEXT,
    year_archive TEXT,
    operator TEXT,
    lease TEXT,
    api_official TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    elevation DOUBLE PRECISION,
    location TEXT,
    shard_id TEXT,
    filename_in_shard TEXT
);
CREATE INDEX IF NOT EXISTS idx_wells_county ON wells (county);
CREATE INDEX IF NOT EXISTS idx_wells_operator ON wells (operator);
CREATE INDEX IF NOT EXISTS idx_wells_api ON wells (api_official);
"""

# must match the FINAL_COLUMNS mapping in the notebook exactly
EXPECTED_COLUMNS = [
    "kgs_id", "api_las", "well_name", "company", "county", "start_depth",
    "stop_depth", "curves", "year_archive", "operator", "lease", "api_official",
    "latitude", "longitude", "elevation", "location", "shard_id", "filename_in_shard",
]


async def main(csv_path: str):
    df = pd.read_csv(csv_path, low_memory=False)
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        print(f"warning: CSV is missing expected columns {missing} - check it matches the notebook's output")
    cols = [c for c in EXPECTED_COLUMNS if c in df.columns]
    df = df[cols].where(pd.notna(df[cols]), None)

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute(SCHEMA)

    records = list(df.itertuples(index=False, name=None))
    col_list = ", ".join(cols)
    placeholders = ", ".join(f"${i + 1}" for i in range(len(cols)))

    await conn.executemany(
        f"""
        INSERT INTO wells ({col_list})
        VALUES ({placeholders})
        ON CONFLICT (kgs_id) DO UPDATE SET
        {", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "kgs_id")}
        """,
        records,
    )
    print(f"loaded {len(records)} rows into wells")
    await conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python db_load.py <path-to-master-csv>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
