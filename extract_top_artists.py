import argparse
import csv
import hashlib
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://ws.audioscrobbler.com/2.0/"
CACHE_DIR = "lastfm_cache"
DEFAULT_TAG = "hyperpop"
DEFAULT_ARTISTS = 100
DEFAULT_PAGES = 20
DEFAULT_OUTPUT = "top_artists.csv"
DEFAULT_SKIPPED_ARTISTS = {"agatka iskra", "laura les", "maple", "mimideath"}


def call_lastfm(api_key, method, **params):
    params.update(method=method, api_key=api_key, format="json")
    cache_key = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as cache_file:
            return json.load(cache_file)

    time.sleep(1.0)
    response = requests.get(
        BASE_URL,
        params=params,
        headers={"User-Agent": "info202-hyperpop-collection/0.1"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Last.fm error {data['error']}: {data.get('message', '')}")

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as cache_file:
        json.dump(data, cache_file)
    return data


def extract_artists(api_key, tag, artist_count, max_pages, skipped_artists):
    artists = []
    seen = set()

    for page in range(1, max_pages + 1):
        data = call_lastfm(
            api_key,
            "tag.getTopArtists",
            tag=tag,
            limit=100,
            page=page,
        )
        page_artists = data.get("topartists", {}).get("artist", [])
        if not page_artists:
            break

        for artist in page_artists:
            name = artist["name"].strip()
            normalized_name = name.casefold()
            if normalized_name in seen or normalized_name in skipped_artists:
                continue
            seen.add(normalized_name)
            artists.append({
                "rank": len(artists) + 1,
                "name": name,
                "mbid": artist.get("mbid", ""),
            })
            if len(artists) == artist_count:
                return artists

    raise RuntimeError(
        f"Only found {len(artists)} artists after checking {max_pages} Last.fm pages; "
        f"need {artist_count}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Extract top artists for a Last.fm tag, excluding selected artists."
    )
    parser.add_argument("--tag", default=DEFAULT_TAG, help=f"Last.fm tag (default: {DEFAULT_TAG})")
    parser.add_argument(
        "--artists",
        type=int,
        default=DEFAULT_ARTISTS,
        help=f"number of artists to output (default: {DEFAULT_ARTISTS})",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=DEFAULT_PAGES,
        help=f"number of Last.fm pages to fetch (default: {DEFAULT_PAGES})",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"CSV output path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--skip-artist",
        action="append",
        default=[],
        metavar="ARTIST",
        help="artist to skip; may be supplied multiple times",
    )
    args = parser.parse_args()

    if args.artists < 1 or args.pages < 1:
        parser.error("--artists and --pages must be positive integers")

    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        parser.error("LASTFM_API_KEY is not set")

    skipped_artists = DEFAULT_SKIPPED_ARTISTS | {
        artist.strip().casefold() for artist in args.skip_artist
    }
    artists = extract_artists(api_key, args.tag, args.artists, args.pages, skipped_artists)

    with open(args.output, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=["rank", "name", "mbid"])
        writer.writeheader()
        writer.writerows(artists)

    print(f"extracted {len(artists)} artists for #{args.tag}")
    print(f"skipped {len(skipped_artists)} configured artists")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
