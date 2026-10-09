if (typeof importScripts === "function") importScripts("lib.js"); // Chrome service worker; Firefox lists lib.js itself

// type "fs" + space in the address bar, then your search
API.omnibox.setDefaultSuggestion({ description: "Search Flowsearch for %s" });
API.omnibox.onInputChanged.addListener(async (text, suggest) => {
  try {
    const r = await fetch((await flowBase()) + "/api/suggest?q=" + encodeURIComponent(text));
    const list = await r.json();
    suggest(list.slice(0, 6).map(s => ({ content: s, description: s })));
  } catch (e) { /* no suggestions */ }
});
API.omnibox.onInputEntered.addListener(async (text, disposition) => {
  const url = (await flowBase()) + "/search?q=" + encodeURIComponent(text);
  if (disposition === "currentTab") API.tabs.update({ url });
  else API.tabs.create({ url, active: disposition === "newForegroundTab" });
});

// the toolbar button shows the temperature of the reading nearest to where you last were
async function refreshBadge() {
  const { loc } = await API.storage.local.get("loc");
  if (!loc) return;
  try {
    const n = nearest(await readings(), loc.la, loc.lo);
    if (!n || n.T == null) return;
    const T = Math.round(n.T);
    await API.action.setBadgeText({ text: String(T) });
    await API.action.setBadgeBackgroundColor({ color: T < 0 ? "#3b82f6" : T < 15 ? "#14b8a6" : T < 25 ? "#d97706" : "#dc2626" });
    await API.action.setTitle({ title: `Groundcheck: ${n.T} °C, ${Math.round(n.km)} km away (${ago(n.t)})` });
  } catch (e) { /* try again at the next alarm */ }
}
API.alarms.create("refresh", { periodInMinutes: 20 });
API.alarms.onAlarm.addListener(a => { if (a.name === "refresh") refreshBadge(); });
API.runtime.onStartup.addListener(refreshBadge);
API.runtime.onInstalled.addListener(refreshBadge);
API.storage.onChanged.addListener((c, area) => { if (area === "local" && c.loc) refreshBadge(); });
