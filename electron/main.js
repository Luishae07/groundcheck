const { app, BrowserWindow, session, Menu } = require('electron');

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    title: 'Groundcheck',
    icon: __dirname + '/icon.png',
  });
  win.loadURL('https://luishae07.github.io/groundcheck/desktop/');

  Menu.setApplicationMenu(Menu.buildFromTemplate([
    {
      label: 'Groundcheck',
      submenu: [{ role: 'about' }, { type: 'separator' }, { role: 'quit' }],
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
