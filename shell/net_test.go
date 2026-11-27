package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func png() []byte {
	b := []byte("\x89PNG\r\n\x1a\n")
	for len(b) < 200 {
		b = append(b, 7)
	}
	return b
}

func srv() *httptest.Server {
	m := http.NewServeMux()
	m.HandleFunc("/p", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`<html><head><title> A &amp; B  عنوان </title><meta property='og:image' content="/img.png"></head></html>`))
	})
	m.HandleFunc("/img.png", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "image/png; charset=x\"")
		w.Write(png())
	})
	m.HandleFunc("/nofav", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("<title>x</title>")) })
	m.HandleFunc("/favicon.ico", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "image/x-icon")
		w.Write(png())
	})
	m.HandleFunc("/evil", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`<title>t</title><meta property="og:image" content="/e.html">`))
	})
	m.HandleFunc("/e.html", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html")
		w.Write(png())
	})
	m.HandleFunc("/gone", func(w http.ResponseWriter, r *http.Request) { http.NotFound(w, r) })
	m.HandleFunc("/nohead", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "HEAD" {
			w.WriteHeader(405)
			return
		}
		w.Write([]byte("ok"))
	})
	return httptest.NewServer(m)
}

func TestFetchMeta(t *testing.T) {
	s := srv()
	defer s.Close()
	var o map[string]string
	json.Unmarshal([]byte(fetchMeta(s.URL+"/p")), &o)
	if o["title"] != "A & B  عنوان" && !strings.Contains(o["title"], "A & B") {
		t.Fatal(o["title"])
	}
	if !strings.HasPrefix(o["image"], "data:image/png;base64,") || strings.ContainsAny(o["image"], "\"; ") && strings.Count(o["image"], ";") > 1 {
		t.Fatal("img", o["image"][:40])
	}
	o = map[string]string{}
	json.Unmarshal([]byte(fetchMeta(s.URL+"/nofav")), &o)
	if !strings.HasPrefix(o["image"], "data:image/x-icon;base64,") {
		t.Fatal("favicon fallback missing")
	}
	o = map[string]string{}
	json.Unmarshal([]byte(fetchMeta(s.URL+"/evil")), &o)
	if o["image"] != "" {
		t.Fatal("non-image content type accepted")
	}
	if fetchMeta("javascript:alert(1)") != "{}" || fetchMeta("file:///etc/passwd") != "{}" {
		t.Fatal("scheme")
	}
	if fetchMeta(s.URL+"/gone") != "{}" {
		t.Fatal("404 should soft fail")
	}
	if fetchMeta("http://127.0.0.1:1/") != "{}" {
		t.Fatal("conn refused should soft fail")
	}
}

func TestCheckURL(t *testing.T) {
	s := srv()
	defer s.Close()
	if c := checkURL(s.URL + "/p"); c != 200 {
		t.Fatal(c)
	}
	if c := checkURL(s.URL + "/gone"); c != 404 {
		t.Fatal(c)
	}
	if c := checkURL(s.URL + "/nohead"); c != 200 {
		t.Fatal("HEAD 405 fallback", c)
	}
	if c := checkURL("http://127.0.0.1:1/"); c != 0 {
		t.Fatal(c)
	}
}
