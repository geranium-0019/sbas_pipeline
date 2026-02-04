#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
from getpass import getpass

import geopandas as gpd
from data_downloader import downloader


def download_s1_slc(
    asf_file: str,
    folder_out: str,
    username: str | None = None,
    password: str | None = None,
) -> None:
    """
    Download Sentinel-1 SLC data from ASF using metadata geojson.

    If username/password are provided, they are written/registered for Earthdata.
    If not provided, this function assumes you already have valid credentials in ~/.netrc.
    """
    out_dir = Path(folder_out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Register credentials only if provided; otherwise rely on existing ~/.netrc
    if username:
        if not password:
            password = getpass("Earthdata password: ")
        netrc = downloader.Netrc()
        netrc.add("urs.earthdata.nasa.gov", username, password)
        print("ℹ️ Credentials were set via downloader.Netrc().")
    else:
        print("ℹ️ No username provided — using existing ~/.netrc credentials (if available).")

    df_asf = gpd.read_file(asf_file)

    if "url" not in df_asf.columns:
        raise ValueError(
            f"'url' column not found in {asf_file}. Available columns: {list(df_asf.columns)}"
        )

    urls = df_asf["url"].dropna().tolist()
    if not urls:
        raise ValueError("No URLs found in the 'url' column.")

    downloader.download_datas(urls, str(out_dir))
    print(f"✅ Download complete. Files saved to {out_dir}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Download Sentinel-1 SLC products from ASF GeoJSON results."
    )
    p.add_argument("--asf-file", required=True, help="Path to ASF results GeoJSON (must include 'url').")
    p.add_argument("--out", required=True, help="Output directory for downloaded files.")
    p.add_argument("--username", default=os.environ.get("EARTHDATA_USERNAME"), help="Earthdata username (optional if ~/.netrc exists).")
    p.add_argument("--password", default=os.environ.get("EARTHDATA_PASSWORD"), help="Earthdata password (optional if ~/.netrc exists).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    download_s1_slc(args.asf_file, args.out, args.username, args.password)


if __name__ == "__main__":
    main()
