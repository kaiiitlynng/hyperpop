# Hyperpop archive

The Vite app renders the 300-track coded collection from `public/data/songs.json`:
a searchable cover grid, and a page per track with lyrics, codes, and Last.fm
metadata.

## Run locally

```bash
npm install
npm run dev
```

## Refresh Last.fm media

Keep the API key server-side in `.env` and run this from the repository root:

```bash
LASTFM_API_KEY=... python extract_lastfm_media.py
```

The script takes songs, lyrics, and codes from `collection.csv`. Songs already in
the manifest keep their Last.fm metadata; new ones are looked up through
`track.getInfo` and `artist.getInfo`, cached in `lastfm_cache/`. The API key is
never included in the generated frontend data.
