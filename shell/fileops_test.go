package main

import (
	"encoding/base64"
	"os"
	"path/filepath"
	"testing"
)

func TestSaveLoadBak(t *testing.T) {
	d := t.TempDir()
	if !saveFile(d, "vault.json", "one") || !saveFile(d, "vault.json", "two") {
		t.Fatal("save")
	}
	if loadFile(d, "vault.json") != "two" {
		t.Fatal("load")
	}
	if b, _ := os.ReadFile(filepath.Join(d, "vault.json.bak")); string(b) != "one" {
		t.Fatal("bak")
	}
	os.Remove(filepath.Join(d, "vault.json")) // corrupted/missing main file falls back to .bak
	if loadFile(d, "vault.json") != "one" {
		t.Fatal("bak fallback")
	}
	if !saveFile(d, "../../evil.txt", "x") {
		t.Fatal()
	}
	if _, err := os.Stat(filepath.Join(d, "evil.txt")); err != nil {
		t.Fatal("path traversal not confined")
	}
	if m, _ := filepath.Glob(filepath.Join(d, "*.tmp")); len(m) != 0 {
		t.Fatal("tmp left")
	}
}

func TestExportInPlace(t *testing.T) {
	d := t.TempDir()
	p := exportFile(d, "../b.html", base64.StdEncoding.EncodeToString([]byte("v1")))
	p2 := exportFile(d, "b.html", base64.StdEncoding.EncodeToString([]byte("v2 mirror")))
	if p == "" || p != p2 || filepath.Dir(p) != filepath.Join(d, "exports") {
		t.Fatal(p, p2)
	}
	if b, _ := os.ReadFile(p); string(b) != "v2 mirror" {
		t.Fatal("not updated in place")
	}
	if exportFile(d, "x", "!!notb64") != "" {
		t.Fatal("bad base64")
	}
	if ents, _ := os.ReadDir(filepath.Join(d, "exports")); len(ents) != 1 {
		t.Fatal("duplicate files created")
	}
}

func TestDirWritable(t *testing.T) {
	if !dirWritable(t.TempDir()) {
		t.Fatal("temp dir should be writable")
	}
	if dirWritable("/nonexistent-raabt-dir") {
		t.Fatal("missing dir must not be writable")
	}
}

func TestBinChunksAndSafety(t *testing.T) {
	d := t.TempDir()
	data := make([]byte, 3*1024*1024+17)
	for i := range data {
		data[i] = byte(i * 7)
	}
	const ch = 3 * 512 * 1024
	for off := 0; off < len(data); off += ch {
		end := off + ch
		if end > len(data) {
			end = len(data)
		}
		if !binWrite(d, "images", "a1.png", base64.StdEncoding.EncodeToString(data[off:end]), off == 0, end == len(data)) {
			t.Fatal("write chunk")
		}
	}
	if binSize(d, "images", "a1.png") != int64(len(data)) {
		t.Fatal("size")
	}
	var got []byte
	for off := int64(0); off < int64(len(data)); off += ch {
		s := binRead(d, "images", "a1.png", off, ch)
		b, _ := base64.StdEncoding.DecodeString(s)
		got = append(got, b...)
	}
	if string(got) != string(data) {
		t.Fatal("roundtrip mismatch")
	}
	for _, bad := range []string{"../x.png", "a/b.png", ".hid", "", "a b.png"} {
		if binWrite(d, "images", bad, "AA==", true, true) {
			t.Fatalf("accepted %q", bad)
		}
	}
	if binWrite(d, "other", "a.png", "AA==", true, true) {
		t.Fatal("bad sub accepted")
	}
	// backup mirror, then delete original, then restore
	binWrite(d, "images", "b2.png", "QUJD", true, true)
	if n := mirrorImages(d, "backup"); n != 2 {
		t.Fatalf("backup copied %d", n)
	}
	binDel(d, "images", "a1.png")
	if mirrorImages(d, "backup") < 0 {
		t.Fatal("rebackup")
	}
	if _, err := os.Stat(filepath.Join(d, "backups", "images", "a1.png")); err == nil {
		t.Fatal("stale backup file kept")
	}
	os.Remove(filepath.Join(d, "images", "b2.png"))
	if n := mirrorImages(d, "restore"); n != 1 {
		t.Fatalf("restore copied %d", n)
	}
	if binSize(d, "images", "b2.png") != 3 {
		t.Fatal("restored file missing")
	}
}

func TestBundledFont(t *testing.T) {
	if bundledFont("cairo-arabic-400.woff2") == "" {
		t.Fatal("cairo missing")
	}
	if bundledFont("../main.go") != "" || bundledFont("nope.woff2") != "" {
		t.Fatal("bad name served")
	}
}

func TestMirrorRestoreBytesAfterImagesDirGone(t *testing.T) {
	d := t.TempDir()
	data := make([]byte, 2*1024*1024+5)
	for i := range data {
		data[i] = byte(i*31 + i/251)
	}
	const ch = 3 * 512 * 1024
	for off := 0; off < len(data); off += ch {
		end := off + ch
		if end > len(data) {
			end = len(data)
		}
		if !binWrite(d, "images", "x1.png", base64.StdEncoding.EncodeToString(data[off:end]), off == 0, end == len(data)) {
			t.Fatal("write")
		}
	}
	if mirrorImages(d, "backup") != 1 {
		t.Fatal("backup")
	}
	if err := os.RemoveAll(filepath.Join(d, "images")); err != nil {
		t.Fatal(err)
	}
	if mirrorImages(d, "restore") != 1 {
		t.Fatal("restore")
	}
	got, err := os.ReadFile(filepath.Join(d, "images", "x1.png"))
	if err != nil || len(got) != len(data) {
		t.Fatalf("restored len %d err %v", len(got), err)
	}
	for i := range data {
		if got[i] != data[i] {
			t.Fatalf("byte %d differs", i)
		}
	}
}
