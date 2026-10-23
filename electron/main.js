const { app, BrowserWindow, session, Menu, ipcMain, net } = require('electron');
const fs = require('fs');
const path = require('path');

// The position the user set by hand (a Google Maps link or plain coordinates), kept in the app's data folder
const locFile = () => path.join(app.getPath('userData'), 'location.json');
let saved = null;
try { saved = JSON.parse(fs.readFileSync(locFile(), 'utf8')); } catch (e) {}
function parseLoc(t) {
  const m = /!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)/.exec(t) || /@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/.exec(t) || /^\s*(-?\d+(?:\.\d+)?)\s*[,; ]\s*(-?\d+(?:\.\d+)?)\s*$/.exec(t);
  if (!m) return null;
  const lat = +m[1], lon = +m[2];
  return Math.abs(lat) <= 90 && Math.abs(lon) <= 180 ? { lat, lon } : null;
}
function askLocation(parent) {
  const w = new BrowserWindow({ width: 520, height: 250, parent, modal: true, resizable: false, title: 'Set my location', autoHideMenuBar: true, webPreferences: { nodeIntegration: true, contextIsolation: false } });
  w.removeMenu();
  const html = `<body style="font:15px system-ui;padding:20px;background:#101924;color:#e8eef4"><p style="margin:0 0 10px">Paste a Google Maps link to your place, or coordinates like <code>52.30, 13.62</code>.</p><input id=t style="width:100%;box-sizing:border-box;padding:9px;font:14px monospace;border-radius:6px;border:1px solid #345;background:#0a1017;color:inherit" autofocus><p id=m style="color:#f0a24a;min-height:1.3em;margin:8px 0"></p><button id=ok style="padding:8px 18px">Save</button> <button id=no style="padding:8px 18px">Cancel</button><script>const {ipcRenderer:r}=require('electron');const t=document.getElementById('t');const go=async()=>{const ok=await r.invoke('gc-setloc',t.value);if(ok)window.close();else document.getElementById('m').textContent='No coordinates found in that.'};document.getElementById('ok').onclick=go;document.getElementById('no').onclick=()=>window.close();t.onkeydown=e=>{if(e.key==='Enter')go()}</script></body>`;
  w.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
}
ipcMain.handle('gc-setloc', (e, text) => {
  const l = parseLoc(String(text || ''));
  if (!l) return false;
  saved = l;
  try { fs.writeFileSync(locFile(), JSON.stringify(l)); } catch (err) {}
  const win = BrowserWindow.getAllWindows().find((x) => !x.getParentWindow());
  if (win) win.reload();
  return true;
});

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    title: 'Groundcheck',
    icon: __dirname + '/icon.png',
    webPreferences: { preload: __dirname + '/preload.js' },
  });
  win.loadURL('https://luishae07.github.io/groundcheck/desktop/');

  Menu.setApplicationMenu(Menu.buildFromTemplate([
    {
      label: 'Groundcheck',
      submenu: [
        { role: 'about' }, { type: 'separator' },
        ...(process.platform === 'linux' ? [
          { label: 'Set my location…', accelerator: 'CmdOrCtrl+L', click: () => askLocation(win) },
          { label: 'Use my internet location', click: () => { saved = null; try { fs.unlinkSync(locFile()); } catch (err) {} win.reload(); } },
          { type: 'separator' },
        ] : []),
        { role: 'quit' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'toggledevtools' }, // Cmd+Alt+I - needed to actually see geolocation errors
        { type: 'separator' },
        { role: 'resetzoom' }, { role: 'zoomin' }, { role: 'zoomout' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
  ]));
}

// Electron checks permissions through TWO separate hooks - a "check" (synchronous,
// "is this allowed right now") and a "request" (the actual prompt flow). Missing either
// one means navigator.geolocation.getCurrentPosition() silently fails and the page just
// falls through to its IP-based fallback, which looks like "location doesn't work" with
// no visible error unless DevTools is open.
// Linux only: city-level position from the IP address (the preload asks for it)
let lastLoc = null;
ipcMain.handle('gc-location', async () => {
  if (saved) return saved;
  if (lastLoc) return lastLoc;
  try {
    const r = await net.fetch('https://ipwho.is/');
    const j = await r.json();
    if (j && j.success !== false && typeof j.latitude === 'number') lastLoc = { lat: j.latitude, lon: j.longitude };
  } catch (e) {}
  return lastLoc;
});

app.whenReady().then(() => {
  session.defaultSession.setPermissionCheckHandler((webContents, permission) => {
    return permission === 'geolocation';
  });
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    callback(permission === 'geolocation');
  });
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
