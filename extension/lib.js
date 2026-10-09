// Shared by the popup and the background script: where Flowsearch and Groundcheck currently live, and
// the nearest-reading maths. Both services run on quick tunnels whose address changes, so the addresses
// are looked up (and cached for 10 minutes) instead of being built in.
const API = globalThis.browser || globalThis.chrome;
const FLOW_POINTER = "https://raw.githubusercontent.com/Luishae07/flowsearch/main/web-tunnel-url.txt";
const GC_PAGE = "https://luishae07.github.io/groundcheck/";

async function cached(key, ttlMs, load) {
  const got = (await API.storage.local.get(key))[key];
  if (got && Date.now() - got.t < ttlMs) return got.v;
  try {
    const v = await load();
    await API.storage.local.set({ [key]: { t: Date.now(), v } });
    return v;
  } catch (e) {
    if (got) return got.v; // an old answer beats none
    throw e;
  }
}

const flowBase = () => cached("flowBase", 10 * 60e3, async () => {
  const r = await fetch(FLOW_POINTER, { cache: "no-store" });
  if (!r.ok) throw new Error("Flowsearch address unavailable");
  return (await r.text()).trim().replace(/\/$/, "");
});

// Groundcheck's page names the data server it talks to; use that server's public /api/data
const dataUrl = () => cached("dataUrl", 10 * 60e3, async () => {
  const html = await (await fetch(GC_PAGE, { cache: "no-store" })).text();
  const m = html.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com(?=\/apiinternel)/);
  if (!m) throw new Error("Groundcheck data address not found");
  return m[0] + "/api/data";
});

async function loadReadings() {
  const r = await fetch(await dataUrl(), { cache: "no-store" });
  if (!r.ok) throw new Error("Groundcheck data answered " + r.status);
  const d = await r.json();
  if (!Array.isArray(d)) throw new Error("unexpected Groundcheck data");
  return d.map(x => ({ id: x.id, t: x.time, T: x.temp, p: x.pressure, h: x.humidity, la: x.lat, lo: x.lon, alt: x.alt }));
}

async function readings() {
  try {
    return await cached("readings", 5 * 60e3, loadReadings);
  } catch (e) {
    await API.storage.local.remove("dataUrl"); // the tunnel may have moved: look it up again once
    return cached("readings", 5 * 60e3, loadReadings);
  }
}

function km(la1, lo1, la2, lo2) {
  const r = Math.PI / 180, dLa = (la2 - la1) * r, dLo = (lo2 - lo1) * r;
  const x = Math.sin(dLa / 2) ** 2 + Math.cos(la1 * r) * Math.cos(la2 * r) * Math.sin(dLo / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(x));
}

// the closest reading, preferring ones from the last 30 days (older ones only if there are none)
function nearest(list, la, lo) {
  const cutoff = Date.now() - 30 * 864e5;
  let pool = list.filter(x => Date.parse(x.t) > cutoff && x.la != null && x.lo != null);
  if (!pool.length) pool = list.filter(x => x.la != null && x.lo != null);
  let best = null, bd = Infinity;
  for (const x of pool) {
    const d = km(la, lo, x.la, x.lo);
    if (d < bd) { bd = d; best = x; }
  }
  return best && { ...best, km: bd };
}

function ago(iso) {
  const s = (Date.now() - Date.parse(iso)) / 1000;
  if (!(s >= 0)) return "just now";
  if (s < 3600) return Math.max(1, Math.round(s / 60)) + " min ago";
  if (s < 86400) return Math.round(s / 3600) + " h ago";
  if (s < 86400 * 60) return Math.round(s / 86400) + " days ago";
  return Math.round(s / 86400 / 30) + " months ago";
}
