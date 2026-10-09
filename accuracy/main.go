// accuracy: which weather model is right? For every weather balloon in Groundcheck's data it takes the
// reading closest to the ground (temperature and humidity as measured), asks Open-Meteo's archive of
// past model runs what each big model had predicted for that place and hour (the latest forecast, the
// one made 1 day earlier and the one made 2 days earlier), and scores the models: average error, bias
// and how often they were within 1 and 2 degrees. Results accumulate in records.jsonl, so every run
// only fetches the new balloons, and accuracy.json holds the scoreboard the web page draws.
package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"math"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

var models = []struct{ ID, Label string }{
	{"ecmwf_ifs025", "ECMWF IFS"},
	{"gfs_seamless", "NOAA GFS"},
	{"icon_seamless", "DWD ICON"},
	{"meteofrance_seamless", "Météo-France ARPEGE/AROME"},
	{"gem_seamless", "Environment Canada GEM"},
	{"ukmo_seamless", "UK Met Office"},
}

type Forecast struct {
	T [3]*float64 `json:"t,omitempty"` // temperature, lead 0 (latest), 1 day, 2 days
	H [3]*float64 `json:"h,omitempty"` // relative humidity
}

type Record struct {
	ID     string              `json:"id"`
	Time   string              `json:"time"` // the hour, UTC
	Lat    float64             `json:"lat"`
	Lon    float64             `json:"lon"`
	Alt    float64             `json:"alt"`
	Elev   float64             `json:"elev"` // height of the model's grid point
	Temp   *float64            `json:"temp,omitempty"`
	Hum    *float64            `json:"hum,omitempty"`
	Models map[string]Forecast `json:"models"`
}

type reading struct {
	ID   string   `json:"id"`
	Time string   `json:"time"`
	Temp *float64 `json:"temp"`
	Hum  *float64 `json:"humidity"`
	Alt  float64  `json:"alt"`
	Lat  float64  `json:"lat"`
	Lon  float64  `json:"lon"`
}

var client = &http.Client{Timeout: 30 * time.Second}

func getJSON(u string, v any) (int, error) {
	req, _ := http.NewRequest("GET", u, nil)
	req.Header.Set("User-Agent", "groundcheck-forecast-accuracy/1.0 (+https://github.com/Luishae07/groundcheck)")
	resp, err := client.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		io.Copy(io.Discard, resp.Body)
		return resp.StatusCode, fmt.Errorf("HTTP %d", resp.StatusCode)
	}
	return 200, json.NewDecoder(io.LimitReader(resp.Body, 64<<20)).Decode(v)
}

// the data server Groundcheck's own page talks to (its address changes, the page always has the current one)
func readingsURL() (string, error) {
	req, _ := http.NewRequest("GET", "https://luishae07.github.io/groundcheck/", nil)
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	html, _ := io.ReadAll(io.LimitReader(resp.Body, 8<<20))
	m := regexp.MustCompile(`https://[a-z0-9-]+\.trycloudflare\.com`).Find(regexp.MustCompile(`https://[a-z0-9-]+\.trycloudflare\.com/apiinternel`).Find(html))
	if m == nil {
		return "", fmt.Errorf("data address not found on the Groundcheck page")
	}
	return string(m) + "/api/data", nil
}

func loadRecords(path string) (recs []Record, seen map[string]bool) {
	seen = map[string]bool{}
	f, err := os.Open(path)
	if err != nil {
		return nil, seen
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1<<20), 16<<20)
	for sc.Scan() {
		var r Record
		if json.Unmarshal(sc.Bytes(), &r) == nil && r.ID != "" {
			recs = append(recs, r)
			seen[r.ID] = true
		}
	}
	return
}

// fetch what every model forecast for the hour of this reading
func forecastFor(rd reading, hour time.Time) (Record, bool, error) {
	day := hour.Format("2006-01-02")
	ids := make([]string, len(models))
	for i, m := range models {
		ids[i] = m.ID
	}
	vars := "temperature_2m,temperature_2m_previous_day1,temperature_2m_previous_day2," +
		"relative_humidity_2m,relative_humidity_2m_previous_day1,relative_humidity_2m_previous_day2"
	u := "https://previous-runs-api.open-meteo.com/v1/forecast?" + url.Values{
		"latitude": {fmt.Sprintf("%.3f", rd.Lat)}, "longitude": {fmt.Sprintf("%.3f", rd.Lon)},
		"hourly": {vars}, "models": {strings.Join(ids, ",")}, "start_date": {day}, "end_date": {day}, "timezone": {"GMT"},
	}.Encode()
	var out struct {
		Elevation float64                    `json:"elevation"`
		Hourly    map[string]json.RawMessage `json:"hourly"`
	}
	if code, err := getJSON(u, &out); err != nil {
		if code == 429 {
			return Record{}, false, fmt.Errorf("rate limited")
		}
		return Record{}, false, err
	}
	h := hour.Hour()
	pick := func(key string) *float64 {
		raw, ok := out.Hourly[key]
		if !ok {
			return nil
		}
		var arr []*float64
		if json.Unmarshal(raw, &arr) != nil || h >= len(arr) {
			return nil
		}
		return arr[h]
	}
	rec := Record{ID: rd.ID, Time: hour.Format("2006-01-02T15:04Z"), Lat: round(rd.Lat, 3), Lon: round(rd.Lon, 3),
		Alt: round(rd.Alt, 0), Elev: out.Elevation, Temp: rd.Temp, Hum: rd.Hum, Models: map[string]Forecast{}}
	any := false
	for _, m := range models {
		var f Forecast
		suffixes := []string{"", "_previous_day1", "_previous_day2"}
		for i, s := range suffixes {
			f.T[i] = pick("temperature_2m" + s + "_" + m.ID)
			f.H[i] = pick("relative_humidity_2m" + s + "_" + m.ID)
			if f.T[i] != nil || f.H[i] != nil {
				any = true
			}
		}
		rec.Models[m.ID] = f
	}
	return rec, any, nil
}

func round(v float64, p int) float64 {
	k := math.Pow(10, float64(p))
	return math.Round(v*k) / k
}

type Score struct {
	N       int     `json:"n"`
	MAE     float64 `json:"mae"`
	Bias    float64 `json:"bias"`
	RMSE    float64 `json:"rmse"`
	Within1 float64 `json:"within1,omitempty"` // share of forecasts within 1 degree (temperature only)
	Within2 float64 `json:"within2,omitempty"`
}

func score(errs []float64, tight bool) *Score {
	if len(errs) == 0 {
		return nil
	}
	var sum, abs, sq float64
	var w1, w2 int
	for _, e := range errs {
		sum += e
		abs += math.Abs(e)
		sq += e * e
		if math.Abs(e) <= 1 {
			w1++
		}
		if math.Abs(e) <= 2 {
			w2++
		}
	}
	n := float64(len(errs))
	s := &Score{N: len(errs), MAE: round(abs/n, 2), Bias: round(sum/n, 2), RMSE: round(math.Sqrt(sq/n), 2)}
	if tight {
		s.Within1, s.Within2 = round(float64(w1)/n*100, 0), round(float64(w2)/n*100, 0)
	}
	return s
}

func main() {
	dir := flag.String("out", "accuracy-data", "folder for records.jsonl and accuracy.json")
	days := flag.Int("days", 365, "only balloons from the last N days")
	maxNew := flag.Int("max-new", 300, "most new balloons to look up in one run")
	flag.Parse()
	os.MkdirAll(*dir, 0o755)
	recPath := filepath.Join(*dir, "records.jsonl")
	recs, seen := loadRecords(recPath)

	// 1. the readings
	src, err := readingsURL()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	var all []reading
	if _, err := getJSON(src, &all); err != nil {
		fmt.Fprintln(os.Stderr, "could not load the readings:", err)
		os.Exit(1)
	}
	// 2. per balloon, the reading closest to the ground
	best := map[string]reading{}
	for _, r := range all {
		if r.ID == "" || r.Temp == nil {
			continue
		}
		if b, ok := best[r.ID]; !ok || r.Alt < b.Alt {
			best[r.ID] = r
		}
	}
	cutoff := time.Now().UTC().AddDate(0, 0, -*days)
	var todo []reading
	for id, r := range best {
		t, err := time.Parse(time.RFC3339, r.Time)
		if err != nil || t.Before(cutoff) || seen[id] || time.Since(t) < 3*time.Hour {
			continue
		}
		todo = append(todo, r)
	}
	sort.Slice(todo, func(i, j int) bool { return todo[i].Time > todo[j].Time })
	if len(todo) > *maxNew {
		todo = todo[:*maxNew]
	}
	fmt.Printf("%d readings, %d balloons already scored, %d new to look up\n", len(all), len(recs), len(todo))

	// 3. what the models said
	f, err := os.OpenFile(recPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	added := 0
	for _, rd := range todo {
		t, _ := time.Parse(time.RFC3339, rd.Time)
		hour := t.UTC().Add(30 * time.Minute).Truncate(time.Hour)
		rec, ok, err := forecastFor(rd, hour)
		if err != nil {
			fmt.Println("stopping early:", err)
			break
		}
		time.Sleep(400 * time.Millisecond)
		if !ok {
			continue
		}
		line, _ := json.Marshal(rec)
		f.Write(append(line, '\n'))
		recs = append(recs, rec)
		added++
	}
	f.Close()
	fmt.Printf("%d new balloons scored\n", added)

	// 4. the scoreboard
	type board struct {
		Label string            `json:"label"`
		Temp  map[string]*Score `json:"temp"`
		Hum   map[string]*Score `json:"humidity"`
	}
	out := map[string]*board{}
	for _, m := range models {
		b := &board{Label: m.Label, Temp: map[string]*Score{}, Hum: map[string]*Score{}}
		for lead := 0; lead < 3; lead++ {
			var te, he []float64
			for _, r := range recs {
				fc, ok := r.Models[m.ID]
				if !ok {
					continue
				}
				if fc.T[lead] != nil && r.Temp != nil && math.Abs(r.Alt-r.Elev) <= 500 {
					adj := *fc.T[lead] - 0.0065*(r.Alt-r.Elev) // the model's grid point is not at the balloon's height
					te = append(te, adj-*r.Temp)
				}
				if fc.H[lead] != nil && r.Hum != nil {
					he = append(he, *fc.H[lead]-*r.Hum)
				}
			}
			key := fmt.Sprint(lead)
			b.Temp[key], b.Hum[key] = score(te, true), score(he, false)
		}
		out[m.ID] = b
	}
	sort.Slice(recs, func(i, j int) bool { return recs[i].Time > recs[j].Time })
	recent := recs
	if len(recent) > 40 {
		recent = recent[:40]
	}
	first, last := "", ""
	if len(recs) > 0 {
		last, first = recs[0].Time, recs[len(recs)-1].Time
	}
	doc := map[string]any{"updated": time.Now().UTC().Format(time.RFC3339), "balloons": len(recs), "from": first, "to": last,
		"leads": []string{"Latest forecast", "Made 1 day before", "Made 2 days before"}, "models": out, "recent": recent}
	data, _ := json.MarshalIndent(doc, "", " ")
	if err := os.WriteFile(filepath.Join(*dir, "accuracy.json"), data, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Printf("scoreboard written: %d balloons\n", len(recs))
}
