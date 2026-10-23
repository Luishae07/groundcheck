const { contextBridge, ipcRenderer } = require('electron');
// Linux has no built-in location service in Electron, so getCurrentPosition would fail.
// This asks the main process for a city-level position (from the IP address) instead.
if (process.platform === 'linux') {
  const get = () => ipcRenderer.invoke('gc-location');
  const toPos = (l) => ({ coords: { latitude: l.lat, longitude: l.lon, accuracy: 5000, altitude: null, altitudeAccuracy: null, heading: null, speed: null }, timestamp: Date.now() });
  const geo = {
    getCurrentPosition(ok, err) { get().then((l) => (l ? ok(toPos(l)) : err && err({ code: 2, message: 'Position unavailable' }))); },
    watchPosition(ok, err) { this.getCurrentPosition(ok, err); return 1; },
    clearWatch() {},
  };
  try { contextBridge.exposeInMainWorld('__gcGeo', geo); } catch (e) {}
  // contextIsolation is on, so the override runs in the page's own world
  const { webFrame } = require('electron');
  webFrame.executeJavaScript(`(() => {
    const pend = new Map(); let id = 0;
    window.addEventListener('message', (e) => { if (e.source === window && e.data && e.data.gcGeoReply) { const p = pend.get(e.data.id); if (p) { pend.delete(e.data.id); p(e.data.pos); } } });
    const ask = () => new Promise((r) => { const i = ++id; pend.set(i, r); window.postMessage({ gcGeoAsk: true, id: i }, '*'); });
    const geo = {
      getCurrentPosition(ok, err) { ask().then((p) => (p ? ok(p) : err && err({ code: 2, message: 'Position unavailable' }))); },
      watchPosition(ok, err) { geo.getCurrentPosition(ok, err); return 1; },
      clearWatch() {},
    };
    Object.defineProperty(navigator, 'geolocation', { value: geo, configurable: true });
  })()`);
  window.addEventListener('message', async (e) => {
    if (e.source === window && e.data && e.data.gcGeoAsk) {
      const l = await get();
      window.postMessage({ gcGeoReply: true, id: e.data.id, pos: l ? toPos(l) : null }, '*');
    }
  });
}
