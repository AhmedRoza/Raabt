package main

import (
	"embed"
	"encoding/base64"
	"regexp"
)

// Only OFL-licensed fonts live here (see LICENSES). Each one is read only when the user selects it.
//
//go:embed fonts/*.woff2
var fontFS embed.FS

var fontName = regexp.MustCompile(`^[a-z0-9-]+\.woff2$`)

func bundledFont(name string) string {
	if !fontName.MatchString(name) {
		return ""
	}
	b, err := fontFS.ReadFile("fonts/" + name)
	if err != nil {
		return ""
	}
	return base64.StdEncoding.EncodeToString(b)
}

// Personal build only: fonts the user supplied himself for his own copy of the program. Their licences are not OFL
// (see PERSONAL-FONTS.txt). They must not be redistributed or published with the program.
//
//go:embed fonts-personal/*
var personalFS embed.FS

var personalName = regexp.MustCompile(`^[a-z0-9-]+\.(ttf|otf)$`)

func personalFont(name string) string {
	if !personalName.MatchString(name) {
		return ""
	}
	b, err := personalFS.ReadFile("fonts-personal/" + name)
	if err != nil {
		return ""
	}
	return base64.StdEncoding.EncodeToString(b)
}
