import { useEffect, useState } from 'react'
import './App.css'

function trackIndexFromPath() {
  const match = window.location.pathname.match(/^\/track\/(\d+)$/)
  return match ? Number(match[1]) : null
}

function App() {
  const [songs, setSongs] = useState([])
  const [trackIndex, setTrackIndex] = useState(trackIndexFromPath)
  const [query, setQuery] = useState('')
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

  useEffect(() => {
    const song = trackIndex === null ? null : songs[trackIndex]
    document.title = song ? `${song.track} by ${song.artist} | Hyperpop archive` : 'Hyperpop archive'
  }, [songs, trackIndex])

  const goTo = (index) => {
    window.history.pushState({}, '', index === null ? '/' : `/track/${index}`)
    setTrackIndex(index)
    window.scrollTo(0, 0)
  }

  const search = (value) => {
    setQuery(value)
    if (trackIndex !== null) goTo(null)
  }

  const song = trackIndex === null ? null : songs[trackIndex]

  let content
  if (loadError) content = <p className="status-message" role="alert">Error: {loadError}</p>
  else if (!songs.length) content = <p className="status-message" role="status">Loading...</p>
  else if (song) content = <TrackPage key={trackIndex} songs={songs} index={trackIndex} onNavigate={goTo} onSearch={search} />
  else content = <IndexPage songs={songs} query={query} onNavigate={goTo} />

  return (
    <>
      <header className="site-header">
        <AppLink className="logo" href="/" onNavigate={() => search('')}>hyperpop</AppLink>
        <form className="search" role="search" onSubmit={(event) => event.preventDefault()}>
          <input
            type="search"
            aria-label="Search tracks, artists, and albums"
            placeholder="Search the archive"
            value={query}
            onChange={(event) => search(event.target.value)}
          />
        </form>
      </header>
      <main className="page">{content}</main>
    </>
  )
}

function AppLink({ href, onNavigate, children, ...props }) {
  return (
    <a {...props} href={href} onClick={(event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
      event.preventDefault()
      onNavigate()
    }}>
      {children}
    </a>
  )
}

function Cover({ song, alt = '', lazy = false }) {
  const [failed, setFailed] = useState(false)
  if (!song.cover_url || failed) return <span className="cover cover-missing">No cover</span>
  return <img className="cover" src={song.cover_url} alt={alt} loading={lazy ? 'lazy' : undefined} onError={() => setFailed(true)} />
}

function CoverLink({ song, index, meta, onNavigate }) {
  return (
    <AppLink className="cover-link" href={`/track/${index}`} onNavigate={() => onNavigate(index)}>
      <Cover song={song} lazy />
      <span className="cover-title">{song.track}</span>
      {meta && <span className="cover-meta">{meta}</span>}
    </AppLink>
  )
}

function IndexPage({ songs, query, onNavigate }) {
  const needle = query.trim().toLowerCase()
  const matches = songs
    .map((song, index) => ({ song, index }))
    .filter(({ song }) => [song.track, song.artist, song.album].some((value) => value?.toLowerCase().includes(needle)))

  return (
    <>
      <div className="index-heading">
        <h1>{needle ? 'Search results' : 'All tracks'}</h1>
        <p className="secondary" role="status">{matches.length} {matches.length === 1 ? 'track' : 'tracks'}</p>
      </div>
      {matches.length === 0 && <p>No track, artist, or album matches “{query.trim()}”.</p>}
      <ul className="cover-grid">
        {matches.map(({ song, index }) => (
          <li key={index}><CoverLink song={song} index={index} meta={song.artist} onNavigate={onNavigate} /></li>
        ))}
      </ul>
    </>
  )
}

function Codes({ title, value }) {
  const codes = (value || '').split(';').map((code) => code.trim()).filter(Boolean)
  if (codes.length === 0) return null
  return (
    <div className="codes">
      <h2 className="section-title">{title}</h2>
      <ul>{codes.map((code) => <li key={code}>{code}</li>)}</ul>
    </div>
  )
}

const formatCount = (value) => Number(value).toLocaleString()

function TrackPage({ songs, index, onNavigate, onSearch }) {
  const song = songs[index]
  const total = songs.length
  const moreTracks = songs
    .map((other, otherIndex) => ({ other, otherIndex }))
    .filter(({ other, otherIndex }) => other.artist === song.artist && otherIndex !== index)

  return (
    <article className="release">
      <div className="release-cover">
        <Cover song={song} alt={`Cover art for ${song.album || song.track}`} />
        {song.lastfm_url && (
          <p className="cover-links"><a href={song.lastfm_url} target="_blank" rel="noreferrer">Open on Last.fm</a></p>
        )}
      </div>

      <header className="release-title">
        <h1>{song.track}</h1>
        <p>by <AppLink href="/" onNavigate={() => onSearch(song.artist)}>{song.artist}</AppLink></p>
      </header>

      <div className="release-main">
        <nav className="track-nav" aria-label="Track navigation">
          <button type="button" className="button" onClick={() => onNavigate((index - 1 + total) % total)}>Previous</button>
          <button type="button" className="button button-primary" onClick={() => onNavigate((index + 1) % total)}>Next track</button>
          <span className="secondary">{index + 1} / {total}</span>
        </nav>
        <section>
          <h2 className="section-title">Lyrics</h2>
          <p className={song.lyrics ? 'lyrics' : 'secondary'}>{song.lyrics || 'Lyrics are not available for this track.'}</p>
        </section>
      </div>

      <section className="release-fans">
        <h2 className="section-title">Details</h2>
        <dl className="metadata">
          {song.album && <div><dt>Album</dt><dd>{song.album}</dd></div>}
          {song.listeners && <div><dt>Artist listeners</dt><dd>{formatCount(song.listeners)}</dd></div>}
          {song.playcount && <div><dt>Track plays</dt><dd>{formatCount(song.playcount)}</dd></div>}
        </dl>
        <Codes title="Themes" value={song.axial_codes} />
        <Codes title="Focused codes" value={song.focused_codes} />
        <Codes title="Initial codes" value={song.initial_codes} />
        {song.queer_reading && (
          <div className="codes">
            <h2 className="section-title">Queer reading</h2>
            <p>{song.queer_reading}</p>
          </div>
        )}
      </section>

      <aside className="release-artist" aria-label={`More by ${song.artist}`}>
        <h2 className="section-title artist-name">{song.artist}</h2>
        <p className="secondary"><AppLink href="/" onNavigate={() => onSearch('')}>Back to archive</AppLink></p>
        {moreTracks.length > 0 && (
          <div className="artist-tracks">
            <h2 className="section-title">More tracks</h2>
            <ul>
              {moreTracks.map(({ other, otherIndex }) => (
                <li key={otherIndex}><CoverLink song={other} index={otherIndex} meta={other.album} onNavigate={onNavigate} /></li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </article>
  )
}

export default App
