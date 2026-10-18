//go:build js && wasm

// Groundcheck map helpers compiled to WebAssembly: grouping of station dots into clusters and the interpolated
// temperature field. The page loads gc.wasm and falls back to plain JavaScript if it cannot.
package main

import (
	"encoding/binary"
	"math"
	"syscall/js"
)

var lats, lons []float64

func readFloats(v js.Value) []float64 {
	b := make([]byte, v.Get("length").Int())
	js.CopyBytesToGo(b, v)
	out := make([]float64, len(b)/8)
	for i := range out {
		out[i] = math.Float64frombits(binary.LittleEndian.Uint64(b[i*8:]))
	}
	return out
}

func toBytes(vals []float64) js.Value {
	b := make([]byte, len(vals)*8)
	for i, f := range vals {
		binary.LittleEndian.PutUint64(b[i*8:], math.Float64bits(f))
	}
	u := js.Global().Get("Uint8Array").New(len(b))
	js.CopyBytesToJS(u, b)
	return u
}

// setPoints(latsBytes, lonsBytes): the stations, in the same order as the page's list.
func setPoints(_ js.Value, a []js.Value) any {
	lats, lons = readFloats(a[0]), readFloats(a[1])
	return len(lats)
}

func project(lat, lon, size float64) (float64, float64) {
	lat = math.Max(-85.0511, math.Min(85.0511, lat))
	x := (lon + 180) / 360 * size
	y := (0.5 - math.Log(math.Tan(math.Pi/4+lat*math.Pi/360))/(2*math.Pi)) * size
	return x, y
}

type cell struct {
	sumLat, sumLon float64
	n              int
	idx            int
}

// clusters(west, south, east, north, zoom, cellPx) -> bytes of float64 records [lat, lon, count, index].
// index is the station for a single dot and -1 for a cluster. cellPx 0 means no grouping.
func clusters(_ js.Value, a []js.Value) any {
	west, south, east, north := a[0].Float(), a[1].Float(), a[2].Float(), a[3].Float()
	zoom, cellPx := a[4].Float(), a[5].Float()
	size := 256 * math.Pow(2, zoom)
	var out []float64
	groups := map[[2]int64]*cell{}
	var order [][2]int64
	for i := range lats {
		la, lo := lats[i], lons[i]
		if la < south || la > north || lo < west || lo > east {
			continue
		}
		if cellPx <= 0 {
			out = append(out, la, lo, 1, float64(i))
			continue
		}
		x, y := project(la, lo, size)
		k := [2]int64{int64(math.Floor(x / cellPx)), int64(math.Floor(y / cellPx))}
		c := groups[k]
		if c == nil {
			c = &cell{idx: i}
			groups[k] = c
			order = append(order, k)
		}
		c.sumLat += la
		c.sumLon += lo
		c.n++
	}
	for _, k := range order {
		c := groups[k]
		if c.n == 1 {
			out = append(out, c.sumLat, c.sumLon, 1, float64(c.idx))
		} else {
			out = append(out, c.sumLat/float64(c.n), c.sumLon/float64(c.n), float64(c.n), -1)
		}
	}
	return toBytes(out)
}

var stops = [][4]float64{
	{0.00, 30, 41, 59}, {0.20, 59, 130, 196}, {0.45, 47, 158, 111},
	{0.70, 201, 154, 46}, {0.88, 192, 90, 60}, {1.00, 140, 30, 30},
}

func heatColor(t float64) (uint8, uint8, uint8) {
	t = math.Max(0, math.Min(1, t))
	a, b := stops[0], stops[len(stops)-1]
	for i := 0; i < len(stops)-1; i++ {
		if t >= stops[i][0] && t <= stops[i+1][0] {
			a, b = stops[i], stops[i+1]
			break
		}
	}
	span := b[0] - a[0]
	if span == 0 {
		span = 1
	}
	f := (t - a[0]) / span
	c := func(k int) uint8 { return uint8(math.Round(a[k] + (b[k]-a[k])*f)) }
	return c(1), c(2), c(3)
}

// heat(pointsBytes [x,y,temp]*, W, H, gridW, gridH, coverPx, fadePx, minT, maxT) -> RGBA bytes of gridW*gridH.
// Same maths as the JavaScript version: inverse-distance weighting, fading out far from any station.
func heat(_ js.Value, a []js.Value) any {
	p := readFloats(a[0])
	W, H := a[1].Float(), a[2].Float()
	gw, gh := a[3].Int(), a[4].Int()
	cover, fade := a[5].Float(), a[6].Float()
	minT, maxT := a[7].Float(), a[8].Float()
	n := len(p) / 3
	rgba := make([]byte, gw*gh*4)
	for gy := 0; gy < gh; gy++ {
		py := (float64(gy) + 0.5) * (H / float64(gh))
		for gx := 0; gx < gw; gx++ {
			px := (float64(gx) + 0.5) * (W / float64(gw))
			var wSum, tSum float64
			minD2 := math.Inf(1)
			for i := 0; i < n; i++ {
				dx, dy := p[i*3]-px, p[i*3+1]-py
				d2 := dx*dx + dy*dy
				if d2 < minD2 {
					minD2 = d2
				}
				q := d2 + 100
				w := 1 / (q * q)
				wSum += w
				tSum += w * p[i*3+2]
			}
			if n == 0 {
				continue
			}
			r, g, b := heatColor((tSum/wSum - minT) / (maxT - minT))
			dist := math.Sqrt(minD2)
			var al float64
			switch {
			case dist <= cover:
				al = 200
			case dist >= fade:
				al = 0
			default:
				al = math.Round(200 * (1 - (dist-cover)/(fade-cover)))
			}
			o := (gy*gw + gx) * 4
			rgba[o], rgba[o+1], rgba[o+2], rgba[o+3] = r, g, b, uint8(al)
		}
	}
	u := js.Global().Get("Uint8Array").New(len(rgba))
	js.CopyBytesToJS(u, rgba)
	return u
}

func main() {
	api := map[string]any{
		"setPoints": js.FuncOf(setPoints),
		"clusters":  js.FuncOf(clusters),
		"heat":      js.FuncOf(heat),
	}
	js.Global().Set("gcwasm", js.ValueOf(api))
	select {}
}
