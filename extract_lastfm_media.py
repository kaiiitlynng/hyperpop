import argparse
import csv
import hashlib
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://ws.audioscrobbler.com/2.0/"
CACHE_DIR = Path("lastfm_cache")


def lastfm_request(api_key, method, **params):
    request_params = {**params, "method": method, "api_key": api_key, "format": "json"}
    cache_path = CACHE_DIR / f"{hashlib.md5(json.dumps(request_params, sort_keys=True).encode()).hexdigest()}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    time.sleep(1)
    response = requests.get(
        BASE_URL,
        params=request_params,
        headers={"User-Agent": "info202-hyperpop-collection/1.0"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Last.fm error {data['error']}: {data.get('message', '')}")
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path.write_text(json.dumps(data), encoding="utf-8")
    return data


def largest_image(images):
    preferred_sizes = ("extralarge", "large", "medium", "small")
    by_size = {image.get("size"): image.get("#text", "").strip() for image in images}
    return next((by_size[size] for size in preferred_sizes if by_size.get(size)), "")


def enrich_track(api_key, row):
    track_data = lastfm_request(api_key, "track.getInfo", artist=row["artist"], track=row["track"])
    track = track_data.get("track", {})
    artist_data = lastfm_request(api_key, "artist.getInfo", artist=row["artist"])
    artist = artist_data.get("artist", {})
    album = track.get("album", {})
    return {
        "track": row["track"],
        "artist": row["artist"],
        "album": row.get("album", "") or album.get("title", ""),
        "year": row.get("year", ""),
        "lyrics": row.get("lyrics", ""),
        "lyrics_status": row.get("lyrics_status", ""),
        "lyrics_source": row.get("lyrics_source", ""),
        "cover_url": largest_image(album.get("image", [])),
        "artist_image_url": largest_image(artist.get("image", [])),
        "lastfm_url": track.get("url", ""),
        "listeners": track.get("listeners", ""),
        "playcount": track.get("playcount", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Enrich a song CSV with cached Last.fm cover and artist images.")
    parser.add_argument("--input", default="hyperpop_top_sample.csv")
    parser.add_argument("--lyrics", default="tracks_with_lyrics.csv")
    parser.add_argument("--output", default="frontend/public/data/songs.json")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        parser.error("LASTFM_API_KEY is not set")

    with open(args.input, newline="", encoding="utf-8") as input_file:
        source_rows = list(csv.DictReader(input_file))
    with open(args.lyrics, newline="", encoding="utf-8") as lyrics_file:
        lyrics_rows = {(row["artist"].casefold(), row["track"].casefold()): row for row in csv.DictReader(lyrics_file)}

    songs = []
    for index, source_row in enumerate(source_rows, 1):
        key = (source_row["artist"].casefold(), source_row["track"].casefold())
        songs.append(enrich_track(api_key, {**source_row, **lyrics_rows.get(key, {})}))
        print(f"[{index}/{len(source_rows)}] {source_row['artist']} - {source_row['track']}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(songs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(songs)} songs to {output_path}")


if __name__ == "__main__":
    main()
