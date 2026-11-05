import csv, hashlib, json, os, random, re, time
from datetime import date
from dotenv import load_dotenv
import requests

load_dotenv()
API_KEY = os.environ["LASTFM_API_KEY"]
BASE = "https://ws.audioscrobbler.com/2.0/"
HEADERS = {"User-Agent": "info202-hyperpop-collection/0.1 (add-your-contact-here)"}
CACHE = "lastfm_cache"
os.makedirs(CACHE, exist_ok=True)

# (tier, min_rank, max_rank, n_artists, n_tracks_each)
TIERS = [("core", 1, 100, 30, 4), ("mid", 101, 400, 35, 3), ("tail", 401, 10**9, 25, 3)]
PERSONAL = []  # [("Artist", "Track"), ...] your own picks, including deliberate false pos/neg
SKIP_TRACKS = {
    ("maple", "fr<3nd"),
    ("a. g. cook", "a-z"),
    ("agatka iskra", "i do coke"),
    ("agatka iskra", "tight dress"),
    ("gupi", "what's known now"),
    ("mimideath", "if god didnt want us to snort worms he wouldn't have made them cylindrical!"),
    ("petal supply", "ddiscombobulated"),
    ("six impala", "spare your enamel, she needs it more than you"),
}
BAD = re.compile(r"\b(remix|mix|sped up|slowed|live|instrumental|acoustic|demo|edit|vip|reprise|version)\b", re.I)
ANNOTATION_COLS = ["year", "collective_label", "vocal_treatment", "genre_fusion",
                   "queer_themes_in_lyrics", "artist_public_queer_identity", "my_membership_judgment"]


def call(method, **params):
    params.update(method=method, api_key=API_KEY, format="json")
    key = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()
    path = f"{CACHE}/{key}.json"
    if os.path.exists(path):
        return json.load(open(path))
    time.sleep(1.0)  # stay polite
    r = requests.get(BASE, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "error" in data:  # last.fm sometimes returns errors with HTTP 200
        return {}
    json.dump(data, open(path, "w"))
    return data


def get_candidates(tag="hyperpop", max_pages=20):
    out, seen = [], set()
    for page in range(1, max_pages + 1):
        arts = call("tag.getTopArtists", tag=tag, limit=100, page=page).get("topartists", {}).get("artist", [])
        if not arts:
            break
        for a in arts:
            if a["name"].lower() not in seen:
                seen.add(a["name"].lower())
                out.append({"name": a["name"], "mbid": a.get("mbid", ""), "rank": len(out) + 1})
    print("candidates:", len(out))
    return out


def artist_tags(name):
    d = call("artist.getTopTags", artist=name, autocorrect=1)
    return {t["name"].lower(): int(t["count"]) for t in d.get("toptags", {}).get("tag", [])}


def artist_stats(name):
    s = call("artist.getInfo", artist=name, autocorrect=1).get("artist", {}).get("stats", {})
    return int(s.get("listeners", 0) or 0), int(s.get("playcount", 0) or 0)


def track_tags(artist, track):
    d = call("track.getTopTags", artist=artist, track=track, autocorrect=1)
    return "; ".join(f'{t["name"].lower()}:{t["count"]}' for t in d.get("toptags", {}).get("tag", [])[:6])


def track_info(artist, track):
    t = call("track.getInfo", artist=artist, track=track, autocorrect=1).get("track", {})
    return t.get("album", {}).get("title", ""), int(t.get("playcount", 0) or 0)


def normalized_track_key(artist, track):
    return artist.casefold(), track.replace("’", "'").casefold()


def pick_tracks(artist, n, rng):
    tracks = call("artist.getTopTracks", artist=artist, autocorrect=1, limit=30).get("toptracks", {}).get("track", [])
    seen, clean = set(), []
    for i, t in enumerate(tracks, 1):
        if normalized_track_key(artist, t["name"]) in SKIP_TRACKS:
            continue
        norm = re.sub(r"\s*[\(\[].*?[\)\]]", "", t["name"]).strip().lower()
        if BAD.search(t["name"]) or norm in seen:
            continue
        seen.add(norm)
        clean.append((i, t))
    pool = clean[1:15]
    if not clean or len(pool) < n - 1:
        return []
    return [clean[0]] + rng.sample(pool, n - 1)


def build_row(artist, mbid, track, tier, artist_rank, source, track_rank=""):
    listeners, plays = artist_stats(artist)
    album, tplays = track_info(artist, track)
    row = {"track": track, "artist": artist, "artist_mbid": mbid, "tier": tier,
           "artist_tag_rank": artist_rank, "hyperpop_tag_strength": artist_tags(artist).get("hyperpop", 0),
           "artist_listeners": listeners, "artist_playcount": plays, "track_rank_in_artist": track_rank,
           "track_playcount": tplays, "album": album, "track_tags": track_tags(artist, track),
           "source": source, "pulled": date.today().isoformat()}
    row.update({c: "" for c in ANNOTATION_COLS})
    return row


def main():
    rng = random.Random(202)  # fixed seed, so the sample is reproducible
    cands = get_candidates()
    rows = []
    for tier, lo, hi, n_artists, n_tracks in TIERS:
        pool = [c for c in cands if lo <= c["rank"] <= hi]
        rng.shuffle(pool)
        got = 0
        for c in pool:
            if got == n_artists:
                break
            picks = pick_tracks(c["name"], n_tracks, rng)
            if not picks:
                continue
            for track_rank, t in picks:
                rows.append(build_row(c["name"], c["mbid"], t["name"], tier, c["rank"], "lastfm", track_rank))
            got += 1
        print(f"{tier}: {got}/{n_artists} artists (pool {len(pool)})")
    for artist, track in PERSONAL:
        rows.append(build_row(artist, "", track, "manual", "", "personal"))
    with open("hyperpop_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows")


if __name__ == "__main__":
    main()