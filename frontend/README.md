# Hyperpop archive

The Vite app renders the 300-track collection from `public/data/songs.json`.
Cards are keyboard accessible and open a detail dialog with CSV metadata,
lyrics, and the Last.fm artist image when one has been enriched.

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

The script uses `lastfm_cache/`, calls `track.getInfo` for album artwork and
`artist.getInfo` for the artist image, then writes the frontend manifest. It
also joins lyrics from `tracks_with_lyrics.csv`. The API key is never included
in the generated frontend data.
