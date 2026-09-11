// Groundcheck is our own official client, so it uses the internal
// unlimited endpoint (not the rate-limited public /api/data, which is for
// third-party consumers). Tunnel hostnames are ephemeral — always fetched
// fresh from GitHub Pages rather than hardcoded, so a tunnel restart never
// breaks the app.
const TUNNEL_URL_FILE = 'https://luishae07.github.io/groundcheck/tunnel-url.txt';
const PREDICTOR_TUNNEL_URL_FILE = 'https://luishae07.github.io/groundcheck/predictor-tunnel-url.txt';

let cachedDataBase: string | null = null;
let cachedPredictorBase: string | null = null;

async function fetchTunnelURL(fileURL: string): Promise<string> {
  const res = await fetch(fileURL);
  if (!res.ok) throw new Error(`tunnel url fetch failed: ${res.status}`);
  const text = (await res.text()).trim();
  if (!text) throw new Error('tunnel url file was empty');
  return text;
}

async function dataBase(): Promise<string> {
  if (!cachedDataBase) cachedDataBase = await fetchTunnelURL(TUNNEL_URL_FILE);
  return cachedDataBase;
}

async function predictorBase(): Promise<string> {
  if (!cachedPredictorBase) cachedPredictorBase = await fetchTunnelURL(PREDICTOR_TUNNEL_URL_FILE);
  return cachedPredictorBase;
}

export type Reading = {
  id: string;
  time: string;
  temp: number;
  alt: number;
  pressure: number | null;
  humidity: number | null;
  lat: number;
  lon: number;
  source: string[];
  tsunix: number;
};

export async function fetchReadings(): Promise<Reading[]> {
  const base = await dataBase();
  const res = await fetch(`${base}/apiinternel/dont/json/microsftwindowssucks/data`);
  if (!res.ok) throw new Error(`data fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchPrediction(lat: number, lon: number) {
  const base = await predictorBase();
  const res = await fetch(`${base}/predict?lat=${lat}&lon=${lon}`);
  if (!res.ok) throw new Error(`predictor fetch failed: ${res.status}`);
  return res.json();
}

export function nearestReading(readings: Reading[], lat: number, lon: number): Reading | null {
  if (!readings.length) return null;
  let best = readings[0];
  let bestD = Infinity;
  for (const r of readings) {
    const d = Math.pow(r.lat - lat, 2) + Math.pow(r.lon - lon, 2);
    if (d < bestD) { bestD = d; best = r; }
  }
  return best;
}
