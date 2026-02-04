'use client';

import { useState } from 'react';

interface Result {
  name: string;
  url: string;
}

interface Quality {
  quality: string;
  link: string;
}

export default function Home() {
  const [query, setQuery] = useState('');
  const [type, setType] = useState<'movie' | 'series'>('movie');
  const [results, setResults] = useState<Result[]>([]);
  const [episodes, setEpisodes] = useState<Result[]>([]);
  const [qualities, setQualities] = useState<Quality[]>([]);
  const [directUrl, setDirectUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<'search' | 'results' | 'episodes' | 'qualities' | 'direct'>('search');
  const [selectedName, setSelectedName] = useState('');

  async function handleSearch() {
    if (!query) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&type=${type}`);
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      if (Array.isArray(data)) {
        setResults(data);
      } else if (data.results) {
        setResults(data.results);
        if (data.results.length === 0 && data.debug) {
          setError(`Debug: ${data.debug.message}`);
        }
      }
      setStep('results');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectResult(result: Result) {
    setLoading(true);
    setError(null);
    setSelectedName(result.name);
    try {
      const res = await fetch(`/api/item?url=${encodeURIComponent(result.url)}`);
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      if (data.type === 'series') {
        setEpisodes(data.episodes);
        setStep('episodes');
      } else {
        setQualities(data.qualities);
        setStep('qualities');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectEpisode(episode: Result) {
    setLoading(true);
    setError(null);
    setSelectedName(prev => `${prev} - ${episode.name}`);
    try {
      const res = await fetch(`/api/item?url=${encodeURIComponent(episode.url)}`);
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setQualities(data.qualities);
      setStep('qualities');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectQuality(quality: Quality) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/direct?link=${encodeURIComponent(quality.link)}`);
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setDirectUrl(data.directUrl);
      setStep('direct');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setStep('search');
    setResults([]);
    setEpisodes([]);
    setQualities([]);
    setDirectUrl(null);
    setError(null);
    setSelectedName('');
  }

  return (
    <div className="container">
      <h1>Akwam-DL Web</h1>

      {error && <div className="error">{error}</div>}

      {step !== 'search' && (
        <div className="bread-crumb" onClick={reset}>
          &larr; Back to Search
        </div>
      )}

      {step === 'search' && (
        <div className="search-box">
          <select value={type} onChange={(e) => setType(e.target.value as any)}>
            <option value="movie">Movies</option>
            <option value="series">Series</option>
          </select>
          <input
            type="text"
            placeholder="Search for movies or series..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button onClick={handleSearch} disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      )}

      {loading && <div className="loading">Processing...</div>}

      {!loading && step === 'results' && (
        <div>
          <h3>Results for &quot;{query}&quot;:</h3>
          <ul className="results-list">
            {results.map((r, i) => (
              <li key={i} onClick={() => handleSelectResult(r)}>{r.name}</li>
            ))}
          </ul>
        </div>
      )}

      {!loading && step === 'episodes' && (
        <div>
          <h3>Episodes for {selectedName}:</h3>
          <ul className="results-list">
            {episodes.map((e, i) => (
              <li key={i} onClick={() => handleSelectEpisode(e)}>{e.name}</li>
            ))}
          </ul>
        </div>
      )}

      {!loading && step === 'qualities' && (
        <div>
          <h3>Select Quality for {selectedName}:</h3>
          <ul className="results-list">
            {qualities.map((q, i) => (
              <li key={i} onClick={() => handleSelectQuality(q)}>{q.quality}</li>
            ))}
          </ul>
        </div>
      )}

      {!loading && step === 'direct' && (
        <div className="direct-link">
          <h3>Your Direct URL:</h3>
          <p>{directUrl}</p>
          <button onClick={() => {
            if (directUrl) navigator.clipboard.writeText(directUrl);
            alert('Copied to clipboard!');
          }}>Copy Link</button>
        </div>
      )}
    </div>
  );
}
