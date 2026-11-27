package main

import (
	"embed"
	"encoding/base64"
	"regexp"
)

// The user's own artwork library (images he sent for folder icons). Read one file at a time, only when the picker opens.
//
//go:embed art/*.webp
var artFS embed.FS

var artName = regexp.MustCompile(`^[ac][0-9]{2}(\.t)?\.webp$`)

func bundledArt(name string) string {
	if !artName.MatchString(name) {
		return ""
	}
	b, err := artFS.ReadFile("art/" + name)
	if err != nil {
		return ""
	}
	return base64.StdEncoding.EncodeToString(b)
}
