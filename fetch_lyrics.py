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
                                  remove_section_headers=True, verbose=False)


def cached_get(url, params):
    key = hashlib.md5(json.dumps({"url": url, "params": params}, sort_keys=True).encode()).hexdigest()
    path = f"{CACHE}/{key}.json"
    if os.path.exists(path):
        return json.load(open(path))
    time.sleep(0.5)  # stay polite
    r = requests.get(url, params=params, timeout=15)
    data = r.json() if r.ok else None
    json.dump(data, open(path, "w"))
    return data


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


def main():
    parser = argparse.ArgumentParser(description="Fetch lyrics for each artist/track pair and write them to a new CSV column.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help=f"source CSV with artist,track columns (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"CSV output path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--misses", default=DEFAULT_MISSES, help=f"CSV of tracks with no lyrics found (default: {DEFAULT_MISSES})")
    parser.add_argument("--limit", type=int, default=None, help="only process the first N rows (for testing)")
    args = parser.parse_args()

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
