import argparse
import csv
import random

from sampling import PERSONAL, build_row, get_candidates, pick_tracks

DEFAULT_ARTISTS = 100
DEFAULT_TRACKS = 3
EXCLUDED_ARTISTS = {"laura les"}


def main():
    parser = argparse.ArgumentParser(description="Sample tracks from the most popular hyperpop artists.")
    parser.add_argument("--artists", type=int, default=DEFAULT_ARTISTS,
                        help=f"number of top artists to sample (default: {DEFAULT_ARTISTS})")
    parser.add_argument("--tracks", type=int, default=DEFAULT_TRACKS,
                        help=f"tracks per artist (default: {DEFAULT_TRACKS})")
    parser.add_argument("--output", default="hyperpop_top_sample.csv",
                        help="CSV output path")
    args = parser.parse_args()

    if args.artists < 1 or args.tracks < 1:
        parser.error("--artists and --tracks must be positive integers")

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

    with open(args.output, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"selected {len(selected)}/{args.artists} top artists with {args.tracks} tracks each")
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
