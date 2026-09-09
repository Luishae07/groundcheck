// Groundcheck status page — checks every live component and serves a
// simple auto-refreshing dashboard, plus a JSON endpoint at /api/status.
package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"sync"
	"time"
)

type Check struct {
	Name      string `json:"name"`
	URL       string `json:"url"`
	OK        bool   `json:"ok"`
	StatusMsg string `json:"status"`
	LatencyMs int64  `json:"latency_ms"`
}

type checkTarget struct {
	name string
	url  string
}

func targets() []checkTarget {
	dataURL := os.Getenv("GROUNDCHECK_STATUS_DATA_URL")
	if dataURL == "" {
		dataURL = "http://localhost:8765/apiinternel/dont/json/microsftwindowssucks/data"
	}
	wsProxyURL := os.Getenv("GROUNDCHECK_STATUS_WS_HEALTH_URL")
	if wsProxyURL == "" {
		wsProxyURL = "http://localhost:8766"
	}
	predictorURL := os.Getenv("GROUNDCHECK_STATUS_PREDICTOR_URL")
	if predictorURL == "" {
		predictorURL = "http://localhost:8768/predict"
	}
	tunnelURL := os.Getenv("GROUNDCHECK_STATUS_TUNNEL_URL")

	list := []checkTarget{
		{"Data API (local)", dataURL},
		{"Live feed proxy", wsProxyURL},
		{"Predictor", predictorURL},
		{"GitHub Pages (mobile)", "https://luishae07.github.io/groundcheck/"},
		{"GitHub Pages (desktop)", "https://luishae07.github.io/groundcheck/desktop/"},
		{"GitHub Pages (wall)", "https://luishae07.github.io/groundcheck/wall/"},
	}
	if tunnelURL != "" {
		list = append(list, checkTarget{"Public tunnel", tunnelURL + "/apiinternel/dont/json/microsftwindowssucks/data"})
	}
	return list
}

func runCheck(t checkTarget) Check {
	client := http.Client{Timeout: 6 * time.Second}
	start := time.Now()
	resp, err := client.Get(t.url)
	latency := time.Since(start).Milliseconds()
	if err != nil {
		return Check{Name: t.name, URL: t.url, OK: false, StatusMsg: "unreachable: " + err.Error(), LatencyMs: latency}
	}
	defer resp.Body.Close()
	// A WebSocket-only server correctly answers a plain HTTP GET with 426
	// Upgrade Required — that's proof it's alive, not a failure.
	ok := (resp.StatusCode >= 200 && resp.StatusCode < 400) || resp.StatusCode == 426
	return Check{Name: t.name, URL: t.url, OK: ok, StatusMsg: fmt.Sprintf("HTTP %d", resp.StatusCode), LatencyMs: latency}
}

func runAllChecks() []Check {
	ts := targets()
	results := make([]Check, len(ts))
	var wg sync.WaitGroup
	for i, t := range ts {
		wg.Add(1)
		go func(i int, t checkTarget) {
			defer wg.Done()
			results[i] = runCheck(t)
		}(i, t)
	}
	wg.Wait()
	return results
}

const pageTemplate = `<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="15">
<title>Groundcheck Status</title>
<style>
:root{--bg:#0a0e14;--panel:#141a22;--line:#232c38;--ink:#eef2f7;--ink-dim:#8a97a8;--ok:#4ade80;--bad:#f87171;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,Segoe UI,Roboto,sans-serif;padding:40px 20px;}
.wrap{max-width:720px;margin:0 auto;}
h1{font-size:24px;margin:0 0 6px;}
.sub{color:var(--ink-dim);font-size:13px;margin-bottom:28px;}
.row{
  display:flex;align-items:center;gap:14px;
  background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:14px 18px;margin-bottom:10px;
}
.dot{width:11px;height:11px;border-radius:50%;flex-shrink:0;}
.dot.ok{background:var(--ok);box-shadow:0 0 8px var(--ok);}
.dot.bad{background:var(--bad);box-shadow:0 0 8px var(--bad);}
.name{font-weight:600;flex:1;}
.meta{font-size:12px;color:var(--ink-dim);text-align:right;font-variant-numeric:tabular-nums;}
.overall{
  display:flex;align-items:center;gap:10px;margin-bottom:20px;
  font-size:15px;font-weight:600;
}
</style></head>
<body><div class="wrap">
<h1>Groundcheck Status</h1>
<div class="sub">Auto-refreshes every 15s &middot; checked {{TIME}}</div>
<div class="overall"><span class="dot {{OVERALL_CLASS}}"></span>{{OVERALL_TEXT}}</div>
{{ROWS}}
</div></body></html>`

func renderPage(checks []Check, checkedAt time.Time) string {
	rows := ""
	allOK := true
	for _, c := range checks {
		cls := "ok"
		if !c.OK {
			cls = "bad"
			allOK = false
		}
		rows += fmt.Sprintf(`<div class="row"><span class="dot %s"></span><span class="name">%s</span><span class="meta">%s &middot; %dms</span></div>`,
			cls, c.Name, c.StatusMsg, c.LatencyMs)
	}
	overallClass := "ok"
	overallText := "All systems operational"
	if !allOK {
		overallClass = "bad"
		overallText = "Some systems degraded"
	}
	page := pageTemplate
	page = replaceAll(page, "{{TIME}}", checkedAt.UTC().Format("2006-01-02 15:04:05 UTC"))
	page = replaceAll(page, "{{OVERALL_CLASS}}", overallClass)
	page = replaceAll(page, "{{OVERALL_TEXT}}", overallText)
	page = replaceAll(page, "{{ROWS}}", rows)
	return page
}

func replaceAll(s, old, new string) string {
	for {
		idx := indexOf(s, old)
		if idx == -1 {
			return s
		}
		s = s[:idx] + new + s[idx+len(old):]
	}
}

func indexOf(s, sub string) int {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return i
		}
	}
	return -1
}

var (
	cacheMu      sync.RWMutex
	cachedChecks []Check
	cachedAt     time.Time
)

func getCachedChecks() ([]Check, time.Time) {
	cacheMu.RLock()
	defer cacheMu.RUnlock()
	return cachedChecks, cachedAt
}

func pollLoop(interval time.Duration) {
	for {
		checks := runAllChecks()
		cacheMu.Lock()
		cachedChecks = checks
		cachedAt = time.Now()
		cacheMu.Unlock()
		time.Sleep(interval)
	}
}

func main() {
	port := os.Getenv("GROUNDCHECK_STATUS_PORT")
	if port == "" {
		port = "8769"
	}

	// Run one check immediately so the first request doesn't see an empty
	// cache, then keep polling every 15s in the background regardless of
	// whether anyone is viewing the page.
	initial := runAllChecks()
	cacheMu.Lock()
	cachedChecks = initial
	cachedAt = time.Now()
	cacheMu.Unlock()
	go pollLoop(15 * time.Second)

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		checks, checkedAt := getCachedChecks()
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Header().Set("Cache-Control", "no-store")
		fmt.Fprint(w, renderPage(checks, checkedAt))
	})

	http.HandleFunc("/api/status", func(w http.ResponseWriter, r *http.Request) {
		checks, checkedAt := getCachedChecks()
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Cache-Control", "no-store")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"checked_at": checkedAt.UTC().Format(time.RFC3339),
			"checks":     checks,
		})
	})

	fmt.Printf("Groundcheck status page on :%s (polling every 15s)\n", port)
	http.ListenAndServe(":"+port, nil)
}
