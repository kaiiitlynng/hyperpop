import argparse
import csv

DEFAULT_INPUT = "hyperpop_top_sample.csv"
DEFAULT_OUTPUT = "tracks.csv"


def main():
    parser = argparse.ArgumentParser(description="Pull artist/track pairs out of the hyperpop sample into their own CSV.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help=f"source CSV (default: {DEFAULT_INPUT})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"CSV output path (default: {DEFAULT_OUTPUT})")
    args = parser.parse_args()

    with open(args.input, newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))

    with open(args.output, "w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=["artist", "track"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"artist": row["artist"].strip(), "track": row["track"].strip()})

    print(f"wrote {len(rows)} artist/track pairs to {args.output}")


if __name__ == "__main__":
    main()
