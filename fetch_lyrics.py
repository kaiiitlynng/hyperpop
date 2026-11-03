import argparse, csv, hashlib, json, os, time
from dotenv import load_dotenv
import requests

load_dotenv()
GENIUS_TOKEN = os.environ.get("GENIUS_TOKEN")  # optional: add to .env to enable the Genius fallback
CACHE = "lyrics_cache"
os.makedirs(CACHE, exist_ok=True)

DEFAULT_INPUT = "tracks.csv"
DEFAULT_OUTPUT = "tracks_with_lyrics.csv"
DEFAULT_MISSES = "missing.csv"

genius = None
if GENIUS_TOKEN:
    import lyricsgenius
    genius = lyricsgenius.Genius(GENIUS_TOKEN, timeout=15, retries=2,
                                  remove_section_headers=True)


def cached_get(url, params, retries=3):
    key = hashlib.md5(json.dumps({"url": url, "params": params}, sort_keys=True).encode()).hexdigest()
    path = f"{CACHE}/{key}.json"
    if os.path.exists(path):
        return json.load(open(path))
    for attempt in range(retries):
        time.sleep(0.5 if attempt == 0 else 2.0 * attempt)  # stay polite, back off on retry
        r = requests.get(url, params=params, timeout=15)
        if r.ok:
            data = r.json()
            json.dump(data, open(path, "w"))  # only cache successes - transient errors shouldn't become permanent misses
            return data
        if r.status_code != 503:
            break
    return None


def from_lrclib(artist, track):
    # exact match first
    data = cached_get("https://lrclib.net/api/get", {"artist_name": artist, "track_name": track})
    if data and data.get("plainLyrics"):
        return data["plainLyrics"], data.get("instrumental", False)
    # fuzzy search fallback
    hits = cached_get("https://lrclib.net/api/search", {"artist_name": artist, "track_name": track})
    if hits:
        for hit in hits:
            if hit.get("plainLyrics"):
                return hit["plainLyrics"], hit.get("instrumental", False)
    return None, False


def from_genius(artist, track):
    if not genius:
        return None
    try:
        song = genius.search_song(track, artist)
        return song.lyrics if song else None
    except Exception:
        return None


def retry_missing(args):
    if not genius:
        raise SystemExit("--retry-missing needs GENIUS_TOKEN set in .env")

    with open(args.output, newline="", encoding="utf-8") as output_file:
        rows = list(csv.DictReader(output_file))

    missing = [row for row in rows if row["lyrics_status"] == "missing"]
    print(f"retrying {len(missing)} missing tracks via Genius")

    recovered = 0
    for i, row in enumerate(missing, 1):
        artist, track = row["artist"], row["track"]
        lyrics = from_genius(artist, track)
        if lyrics:
            row["lyrics"] = lyrics
            row["lyrics_source"] = "genius"
            row["lyrics_status"] = "ok"
            recovered += 1
        print(f"[{i}/{len(missing)}] {'ok' if lyrics else 'missing':12} {artist} - {track}")
        time.sleep(0.5)  # stay polite

    with open(args.output, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=["artist", "track", "lyrics", "lyrics_source", "lyrics_status"])
        writer.writeheader()
        writer.writerows(rows)

    still_missing = [{"artist": row["artist"], "track": row["track"]} for row in rows if row["lyrics_status"] == "missing"]
    with open(args.misses, "w", newline="", encoding="utf-8") as misses_file:
        writer = csv.DictWriter(misses_file, fieldnames=["artist", "track"])
        writer.writeheader()
        writer.writerows(still_missing)

    print(f"done: recovered {recovered}/{len(missing)} via Genius, {len(still_missing)} still missing -> {args.output}")


def main():
    parser = argparse.ArgumentParser(description="Fetch lyrics for each artist/track pair and write them to a new CSV column.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help=f"source CSV with artist,track columns (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"CSV output path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--misses", default=DEFAULT_MISSES, help=f"CSV of tracks with no lyrics found (default: {DEFAULT_MISSES})")
    parser.add_argument("--limit", type=int, default=None, help="only process the first N rows (for testing)")
    parser.add_argument("--retry-missing", action="store_true",
                        help="skip lrclib and only retry, via Genius, the rows already marked 'missing' in --output")
    args = parser.parse_args()

    if args.retry_missing:
        retry_missing(args)
        return

    with open(args.input, newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    if args.limit:
        rows = rows[:args.limit]

    results, misses = [], []
    for i, row in enumerate(rows, 1):
        artist, track = row["artist"].strip(), row["track"].strip()
        lyrics, instrumental, source = None, False, None
        try:
            lyrics, instrumental = from_lrclib(artist, track)
            source = "lrclib" if lyrics else None
        except requests.RequestException:
            pass
        if not lyrics and not instrumental:
            lyrics = from_genius(artist, track)
            source = "genius" if lyrics else source

        status = "instrumental" if instrumental else ("ok" if lyrics else "missing")
        print(f"[{i}/{len(rows)}] {status:12} {artist} - {track}")
        results.append({"artist": artist, "track": track, "lyrics": lyrics or "",
                        "lyrics_source": source or "", "lyrics_status": status})
        if status == "missing":
            misses.append({"artist": artist, "track": track})

    with open(args.output, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=["artist", "track", "lyrics", "lyrics_source", "lyrics_status"])
        writer.writeheader()
        writer.writerows(results)

    with open(args.misses, "w", newline="", encoding="utf-8") as misses_file:
        writer = csv.DictWriter(misses_file, fieldnames=["artist", "track"])
        writer.writeheader()
        writer.writerows(misses)

    found = len(rows) - len(misses)
    print(f"done: {found}/{len(rows)} found, {len(misses)} missing -> {args.output}")


if __name__ == "__main__":
    main()
