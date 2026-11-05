import argparse
import csv
import random

from sampling import PERSONAL, build_row, get_candidates, pick_tracks

DEFAULT_ARTISTS = 100
DEFAULT_TRACKS = 3
EXCLUDED_ARTISTS = {"laura les", "maple", "agatka iskra", "mimideath"}


def read_artist_file(path):
    with open(path, newline="", encoding="utf-8") as artist_file:
        rows = list(csv.reader(artist_file))

    if not rows:
        return []
    headers = [header.strip().casefold() for header in rows[0]]
    if "name" in headers:
        name_index = headers.index("name")
        return [
            row[name_index].strip()
            for row in rows[1:]
            if len(row) > name_index and row[name_index].strip()
        ]
    return [row[0].strip() for row in rows if row and row[0].strip()]


def write_rows(path, rows):
    if not rows:
        raise RuntimeError("No track rows to write")
    with open(path, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def sample_specific_artists(artists, tracks, rng):
    rows = []
    for artist in artists:
        picks = pick_tracks(artist, tracks, rng)
        if not picks:
            raise RuntimeError(f"Could not find {tracks} clean tracks for {artist}")
        for track_rank, track in picks:
            rows.append(build_row(
                artist, "", track["name"], "specific", "", "lastfm", track_rank,
            ))
    return rows


def main():
    parser = argparse.ArgumentParser(description="Sample tracks from the most popular hyperpop artists.")
    parser.add_argument("--artists", type=int, default=DEFAULT_ARTISTS,
                        help=f"number of top artists to sample (default: {DEFAULT_ARTISTS})")
    parser.add_argument("--tracks", type=int, default=DEFAULT_TRACKS,
                        help=f"tracks per artist (default: {DEFAULT_TRACKS})")
    parser.add_argument("--artist", action="append", default=[],
                        help="specific artist to sample; may be supplied multiple times")
    parser.add_argument("--artists-file",
                        help="file of specific artists, one per line or a CSV with a name column")
    parser.add_argument("--output", default="hyperpop_top_sample.csv",
                        help="CSV output path")
    args = parser.parse_args()

    if args.artists < 1 or args.tracks < 1:
        parser.error("--artists and --tracks must be positive integers")

    if args.artist and args.artists_file:
        parser.error("use either --artist or --artists-file, not both")
    if args.artist or args.artists_file:
        specific_artists = args.artist or read_artist_file(args.artists_file)
        if not specific_artists:
            parser.error("specific artist input is empty")
        rows = sample_specific_artists(specific_artists, args.tracks, random.Random(202))
        write_rows(args.output, rows)
        print(f"sampled {len(specific_artists)} specific artists with {args.tracks} tracks each")
        print(f"wrote {len(rows)} rows to {args.output}")
        return

    rng = random.Random(202)
    candidates = get_candidates(max_pages=20)
    selected = []
    rows = []

    for artist in candidates:
        if len(selected) == args.artists:
            break
        if artist["name"].strip().casefold() in EXCLUDED_ARTISTS:
            continue
        picks = pick_tracks(artist["name"], args.tracks, rng)
        if not picks:
            continue
        selected.append(artist)
        for track_rank, track in picks:
            rows.append(build_row(
                artist["name"], artist["mbid"], track["name"], "top",
                artist["rank"], "lastfm", track_rank,
            ))

    if len(selected) != args.artists:
        raise RuntimeError(f"Only found {len(selected)} artists with {args.tracks} clean tracks")

    for artist, track in PERSONAL:
        rows.append(build_row(artist, "", track, "manual", "", "personal"))

    write_rows(args.output, rows)

    print(f"selected {len(selected)}/{args.artists} top artists with {args.tracks} tracks each")
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
