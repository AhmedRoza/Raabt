package main

import (
	"encoding/base64"
	"encoding/json"
	"html"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"
)

var httpc = &http.Client{Timeout: 8 * time.Second}

func get(u string, limit int64) ([]byte, string, int, error) {
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, "", 0, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Raabt/1.0")
	resp, err := httpc.Do(req)
	if err != nil {
		return nil, "", 0, err
	}
	defer resp.Body.Close()
	b, _ := io.ReadAll(io.LimitReader(resp.Body, limit))
	return b, resp.Header.Get("Content-Type"), resp.StatusCode, nil
}

var reTitle = regexp.MustCompile(`(?is)<title[^>]*>(.*?)</title>`)
var reMeta = regexp.MustCompile(`(?is)<meta\s[^>]*>`)
var reAttr = regexp.MustCompile(`(?is)(property|name|content)\s*=\s*("([^"]*)"|'([^']*)')`)

// fetchMeta returns {"title":..., "image":"data:image/...;base64,..."}. Fails soft: empty fields.
func fetchMeta(u string) string {
	out := map[string]string{}
	pu, err := url.Parse(u)
	if err != nil || (pu.Scheme != "http" && pu.Scheme != "https") {
		return "{}"
	}
	body, _, code, err := get(u, 1<<20)
	if err != nil || code >= 400 {
		return "{}"
	}
	page := string(body)
	if m := reTitle.FindStringSubmatch(page); m != nil {
		out["title"] = strings.TrimSpace(html.UnescapeString(m[1]))
	}
	img := ""
	for _, tag := range reMeta.FindAllString(page, -1) {
		var prop, content string
		for _, a := range reAttr.FindAllStringSubmatch(tag, -1) {
			v := a[3] + a[4]
			switch strings.ToLower(a[1]) {
			case "property", "name":
				prop = strings.ToLower(v)
			case "content":
				content = html.UnescapeString(v)
			}
		}
		if (prop == "og:image" || prop == "twitter:image") && content != "" && img == "" {
			img = content
		}
	}
	if img == "" {
		img = pu.Scheme + "://" + pu.Host + "/favicon.ico"
	}
	if ref, err := pu.Parse(img); err == nil {
		if b, ct, c, err := get(ref.String(), 2<<20); err == nil && c < 400 && len(b) > 100 && okImageType(ct) {
			out["image"] = "data:" + strings.ToLower(strings.TrimSpace(strings.SplitN(ct, ";", 2)[0])) + ";base64," + base64.StdEncoding.EncodeToString(b)
		}
	}
	j, _ := json.Marshal(out)
	return string(j)
}

func checkURL(u string) int {
	req, err := http.NewRequest("HEAD", u, nil)
	if err != nil {
		return 0
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 Raabt/1.0")
	resp, err := httpc.Do(req)
	if err != nil {
		return 0
	}
	resp.Body.Close()
	if resp.StatusCode == 405 || resp.StatusCode == 403 {
		_, _, c, err := get(u, 1024)
		if err == nil {
			return c
		}
	}
	return resp.StatusCode
}

// okImageType accepts only plain raster/vector image content types (no parameters that could break the data: URL).
func okImageType(ct string) bool {
	ct = strings.ToLower(strings.TrimSpace(strings.SplitN(ct, ";", 2)[0]))
	switch ct {
	case "image/png", "image/jpeg", "image/gif", "image/webp", "image/x-icon", "image/vnd.microsoft.icon", "image/svg+xml", "image/avif":
		return true
	}
	return false
}
