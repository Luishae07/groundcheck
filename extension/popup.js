const $ = id => document.getElementById(id);
$("gc").href = GC_PAGE;

$("f").addEventListener("submit", async e => {
  e.preventDefault();
  const q = $("q").value.trim();
  if (!q) return;
  try {
    await API.tabs.create({ url: (await flowBase()) + "/search?q=" + encodeURIComponent(q) });
    window.close();
  } catch (err) {
    $("wx").innerHTML = '<span class="err">Flowsearch is not reachable right now.</span>';
  }
});

function locate(force) {
  return new Promise(async (resolve, reject) => {
    const { loc } = await API.storage.local.get("loc");
    if (loc && !force && Date.now() - loc.t < 3600e3) return resolve(loc);
    navigator.geolocation.getCurrentPosition(p => {
      const l = { la: p.coords.latitude, lo: p.coords.longitude, t: Date.now() };
      API.storage.local.set({ loc: l });
      resolve(l);
    }, err => (loc ? resolve(loc) : reject(err)), { timeout: 15000, maximumAge: 600000 });
  });
}

async function show(force) {
  $("wx").innerHTML = '<span class="dim">Finding where you are…</span>';
  let l;
  try { l = await locate(force); }
  catch (e) {
    $("wx").innerHTML = '<span class="err">Could not get your location.</span><p class="dim">Allow location for this extension, then press “Use my location”.</p>';
    return;
  }
  $("wx").innerHTML = '<span class="dim">Looking up the nearest Groundcheck reading…</span>';
  try {
    const n = nearest(await readings(), l.la, l.lo);
    if (!n) throw new Error("no readings");
    const f = v => (v == null ? "–" : v);
    $("wx").innerHTML = `<div id="temp">${f(n.T)}<small> °C</small></div>
      <div class="row"><span>Humidity <b>${f(n.h)} %</b></span><span>Pressure <b>${f(n.p)} hPa</b></span></div>
      <div class="row"><span><b>${Math.round(n.km)} km</b> away</span><span>${ago(n.t)}</span></div>
      <div class="dim" style="margin-top:6px;font-size:12px">Reading ${n.id}, at ${Math.round(n.alt || 0)} m</div>`;
  } catch (e) {
    $("wx").innerHTML = '<span class="err">Groundcheck data is not reachable right now.</span>';
  }
}
$("loc").addEventListener("click", () => show(true));
show(false);
