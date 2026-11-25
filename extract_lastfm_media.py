import argparse
import csv
import hashlib
import json
import os
import time
import unicodedata
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://ws.audioscrobbler.com/2.0/"
CACHE_DIR = Path("lastfm_cache")
# Last.fm's blank star, returned when it has no image.
PLACEHOLDER_IMAGE = "2a96cbd8b46e442fc41c2b86b821562f"
CODING_FIELDS = ("lyric_basis", "initial_codes", "focused_codes", "axial_codes", "queer_reading")


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
    url = next((by_size[size] for size in preferred_sizes if by_size.get(size)), "")
    return "" if PLACEHOLDER_IMAGE in url else url


def song_key(row):
    return tuple(unicodedata.normalize("NFC", row[field]).strip().casefold() for field in ("artist", "track"))


def fetch_media(api_key, row):
    track = lastfm_request(api_key, "track.getInfo", artist=row["artist"], track=row["track"]).get("track", {})
    artist = lastfm_request(api_key, "artist.getInfo", artist=row["artist"]).get("artist", {})
    album = track.get("album", {})
    return {
        "album": album.get("title", ""),
        "cover_url": largest_image(album.get("image", [])),
        "artist_image_url": largest_image(artist.get("image", [])),
        "lastfm_url": track.get("url", ""),
        "listeners": artist.get("stats", {}).get("listeners", ""),
        "playcount": track.get("playcount", ""),
    }


def build_song(row, media):
    artist_image = media["artist_image_url"]
    return {
        "track": row["track"],
        "artist": row["artist"],
        "lyrics": row["lyrics"],
        **{field: row[field] for field in CODING_FIELDS},
        "album": media["album"],
        "cover_url": media["cover_url"],
        "artist_image_url": "" if PLACEHOLDER_IMAGE in artist_image else artist_image,
        "lastfm_url": media["lastfm_url"],
        "listeners": media["listeners"],
        "playcount": media["playcount"],
    }


def main():
    parser = argparse.ArgumentParser(description="Build the frontend song manifest from the coded collection.")
    parser.add_argument("--input", default="collection.csv")
    parser.add_argument("--output", default="frontend/public/data/songs.json")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        parser.error("LASTFM_API_KEY is not set")

    with open(args.input, newline="", encoding="utf-8-sig") as input_file:
        rows = list(csv.DictReader(input_file))

    output_path = Path(args.output)
    known = {}
    if output_path.exists():
        known = {song_key(song): song for song in json.loads(output_path.read_text(encoding="utf-8"))}

    empty = dict.fromkeys(("album", "cover_url", "artist_image_url", "lastfm_url", "listeners", "playcount"), "")
    songs = []
    for index, row in enumerate(rows, 1):
        media = known.get(song_key(row))
        if media is None:
            try:
                media = fetch_media(api_key, row)
            except (requests.RequestException, RuntimeError) as error:
                # The request URL in an HTTP error contains the API key, so don't print it.
                detail = error if isinstance(error, RuntimeError) else type(error).__name__
                print(f"no media for {row['artist']} - {row['track']}: {detail}")
                media = empty
            else:
                print(f"[{index}/{len(rows)}] {row['artist']} - {row['track']}")
        songs.append(build_song(row, media))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(songs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(songs)} songs to {output_path}")


if __name__ == "__main__":
    main()
