import { useEffect, useState } from 'react'
import './App.css'

const FALLBACK_COVER = 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?auto=format&fit=crop&w=800&q=80'

function trackIndexFromPath() {
  const match = window.location.pathname.match(/^\/track\/(\d+)$/)
  return match ? Number(match[1]) : null
}

function App() {
  const [songs, setSongs] = useState([])
  const [trackIndex, setTrackIndex] = useState(trackIndexFromPath)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    fetch('/data/songs.json')
      .then((response) => {
        if (!response.ok) throw new Error('Could not load the song collection.')
        return response.json()
      })
      .then(setSongs)
      .catch((error) => setLoadError(error.message))
  }, [])

  useEffect(() => {
    const syncRoute = () => setTrackIndex(trackIndexFromPath())
    window.addEventListener('popstate', syncRoute)
    return () => window.removeEventListener('popstate', syncRoute)
  }, [])

  const goTo = (index) => {
    window.history.pushState({}, '', index === null ? '/' : `/track/${index}`)
    setTrackIndex(index)
    window.scrollTo(0, 0)
  }

  if (loadError) return <p className="status-message error">{loadError}</p>
  if (!songs.length) return <p className="status-message">Loading...</p>

  if (trackIndex !== null && songs[trackIndex]) {
    return <TrackPage song={songs[trackIndex]} index={trackIndex} total={songs.length} onNavigate={goTo} />
  }

  return (
    <main className="app-shell">
      <section className="song-grid" aria-label="Song collection">
        {songs.map((song, index) => (
          <a className="song-card" href={`/track/${index}`} key={`${song.artist}-${song.track}-${index}`} onClick={(event) => {
            event.preventDefault()
            goTo(index)
          }}>
            <div className="cover-wrap">
              <img src={song.cover_url || song.artist_image_url || FALLBACK_COVER} alt="" onError={(event) => { event.currentTarget.src = FALLBACK_COVER }} />
            </div>
            <span className="song-title">{song.track}</span>
            <span className="song-artist">{song.artist}</span>
          </a>
        ))}
      </section>
    </main>
  )
}

function TrackPage({ song, index, total, onNavigate }) {
  const previous = index > 0 ? index - 1 : total - 1
  const next = index < total - 1 ? index + 1 : 0

  return (
    <main className="track-page">
      <nav className="track-nav" aria-label="Track navigation">
        <button onClick={() => onNavigate(previous)} aria-label="Previous track">←</button>
        <button onClick={() => onNavigate(null)} className="back-link">All tracks</button>
        <button onClick={() => onNavigate(next)} aria-label="Next track">→</button>
      </nav>
      <article className="track-content">
        <div className="track-image">
          <img src={song.artist_image_url || song.cover_url || FALLBACK_COVER} alt={`${song.artist}`} onError={(event) => { event.currentTarget.src = FALLBACK_COVER }} />
        </div>
        <div className="track-copy">
          <p className="track-kicker">{String(index + 1).padStart(3, '0')} / {total}</p>
          <h1>{song.track}</h1>
          <p className="track-artist">{song.artist}</p>
          <dl className="metadata">
            <div><dt>Album</dt><dd>{song.album || 'Unknown album'}</dd></div>
            <div><dt>Year</dt><dd>{song.year || '—'}</dd></div>
            <div><dt>Listeners</dt><dd>{song.listeners ? Number(song.listeners).toLocaleString() : '—'}</dd></div>
          </dl>
          <div className="lyrics">
            <p className="lyrics-label">Lyrics</p>
            <p>{song.lyrics || 'Lyrics are not available for this track.'}</p>
          </div>
          {song.lastfm_url && <a className="lastfm-link" href={song.lastfm_url} target="_blank" rel="noreferrer">Open on Last.fm ↗</a>}
        </div>
      </article>
    </main>
  )
}

export default App
