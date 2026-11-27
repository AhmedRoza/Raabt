package main

import (
	"encoding/base64"
	"os"
	"path/filepath"
)

// saveFile writes atomically (tmp + rename) and keeps one rolling .bak of the previous content.
func saveFile(dir, name, data string) bool {
	p := filepath.Join(dir, filepath.Base(name))
	if old, err := os.ReadFile(p); err == nil && len(old) > 0 {
		_ = os.WriteFile(p+".bak", old, 0o644)
	}
	if os.WriteFile(p+".tmp", []byte(data), 0o644) != nil {
		return false
	}
	return os.Rename(p+".tmp", p) == nil
}

func loadFile(dir, name string) string {
	b, err := os.ReadFile(filepath.Join(dir, filepath.Base(name)))
	if err != nil {
		b, _ = os.ReadFile(filepath.Join(dir, filepath.Base(name)) + ".bak")
	}
	return string(b)
}

// exportFile decodes base64 into dir/exports/<base name>, replacing the file in place. Returns the path or "".
func exportFile(dir, name, b64 string) string {
	b, err := base64.StdEncoding.DecodeString(b64)
	if err != nil {
		return ""
	}
	d := filepath.Join(dir, "exports")
	if os.MkdirAll(d, 0o755) != nil {
		return ""
	}
	p := filepath.Join(d, filepath.Base(name))
	if os.WriteFile(p, b, 0o644) != nil {
		return ""
	}
	return p
}

// dirWritable reports whether a file can be created in dir (read-only folders, locked USB sticks).
func dirWritable(dir string) bool {
	p := filepath.Join(dir, ".w")
	if os.WriteFile(p, []byte("x"), 0o644) != nil {
		return false
	}
	return os.Remove(p) == nil
}

// ---- binary side files: images (clipboard section) and user fonts ----

var binSubs = map[string]bool{"images": true, "fonts": true}

func safeBinName(n string) bool {
	if n == "" || len(n) > 90 || n[0] == '.' {
		return false
	}
	for _, c := range n {
		if !(c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' || c == '.' || c == '_' || c == '-') {
			return false
		}
	}
	return true
}

func binPath(dir, sub, name string) string {
	if !binSubs[sub] || !safeBinName(name) {
		return ""
	}
	return filepath.Join(dir, sub, name)
}

// binWrite appends one base64 chunk. The first chunk starts a .part file, the last renames it into place,
// so a half-written image never shows up as a real file.
func binWrite(dir, sub, name, b64 string, first, last bool) bool {
	p := binPath(dir, sub, name)
	if p == "" {
		return false
	}
	b, err := base64.StdEncoding.DecodeString(b64)
	if err != nil {
		return false
	}
	if os.MkdirAll(filepath.Dir(p), 0o755) != nil {
		return false
	}
	flag := os.O_WRONLY | os.O_CREATE | os.O_APPEND
	if first {
		flag = os.O_WRONLY | os.O_CREATE | os.O_TRUNC
	}
	f, err := os.OpenFile(p+".part", flag, 0o644)
	if err != nil {
		return false
	}
	_, werr := f.Write(b)
	cerr := f.Close()
	if werr != nil || cerr != nil {
		return false
	}
	if last {
		return os.Rename(p+".part", p) == nil
	}
	return true
}

func binSize(dir, sub, name string) int64 {
	p := binPath(dir, sub, name)
	if p == "" {
		return -1
	}
	st, err := os.Stat(p)
	if err != nil {
		return -1
	}
	return st.Size()
}

// binRead returns one base64 chunk. off and n are in bytes; callers use multiples of 3 so chunks concatenate.
func binRead(dir, sub, name string, off, n int64) string {
	p := binPath(dir, sub, name)
	if p == "" || off < 0 || n <= 0 || n > 4<<20 {
		return ""
	}
	f, err := os.Open(p)
	if err != nil {
		return ""
	}
	defer f.Close()
	buf := make([]byte, n)
	m, _ := f.ReadAt(buf, off)
	return base64.StdEncoding.EncodeToString(buf[:m])
}

func binDel(dir, sub, name string) bool {
	p := binPath(dir, sub, name)
	if p == "" {
		return false
	}
	_ = os.Remove(p + ".part")
	err := os.Remove(p)
	return err == nil || os.IsNotExist(err)
}

// mirrorImages: "backup" makes backups/images an exact copy of images (stale files removed);
// "restore" copies back only the files that are missing from images. Returns the number of files copied.
func mirrorImages(dir, mode string) int {
	src, dst := filepath.Join(dir, "images"), filepath.Join(dir, "backups", "images")
	if mode == "restore" {
		src, dst = dst, src
	} else if mode != "backup" {
		return -1
	}
	if os.MkdirAll(dst, 0o755) != nil {
		return -1
	}
	ents, _ := os.ReadDir(src)
	n := 0
	have := map[string]bool{}
	for _, e := range ents {
		if e.IsDir() || filepath.Ext(e.Name()) == ".part" {
			continue
		}
		have[e.Name()] = true
		sp, dp := filepath.Join(src, e.Name()), filepath.Join(dst, e.Name())
		si, err := e.Info()
		if err != nil {
			continue
		}
		if di, err := os.Stat(dp); err == nil && di.Size() == si.Size() && (mode == "restore" || !di.ModTime().Before(si.ModTime())) {
			continue
		}
		if mode == "restore" {
			if _, err := os.Stat(dp); err == nil {
				continue
			}
		}
		b, err := os.ReadFile(sp)
		if err != nil || os.WriteFile(dp+".tmp", b, 0o644) != nil || os.Rename(dp+".tmp", dp) != nil {
			continue
		}
		n++
	}
	if mode == "backup" {
		old, _ := os.ReadDir(dst)
		for _, e := range old {
			if !e.IsDir() && !have[e.Name()] {
				_ = os.Remove(filepath.Join(dst, e.Name()))
			}
		}
	}
	return n
}

// saveFileTo writes into an absolute folder the user picked in Settings (backup location).
func saveFileTo(dir, name, data string) bool {
	dir = filepath.Clean(dir)
	if dir == "" || !filepath.IsAbs(dir) {
		return false
	}
	if st, err := os.Stat(dir); err != nil || !st.IsDir() {
		return false
	}
	p := filepath.Join(dir, filepath.Base(name))
	if old, err := os.ReadFile(p); err == nil && len(old) > 0 {
		_ = os.WriteFile(p+".bak", old, 0o644)
	}
	if os.WriteFile(p+".tmp", []byte(data), 0o644) != nil {
		return false
	}
	return os.Rename(p+".tmp", p) == nil
}
