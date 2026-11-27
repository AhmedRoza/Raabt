//go:build windows

package main

import (
	"os"

	"golang.org/x/sys/windows/registry"
)

var browserExe = map[string]string{"firefox": "firefox", "brave": "brave", "vivaldi": "vivaldi", "floorp": "floorp", "librewolf": "librewolf", "chrome": "chrome", "msedge": "msedge"}

// setAutostart writes/removes this user's Run entry only when the user toggles the setting.
func setAutostart(on bool) {
	k, err := registry.OpenKey(registry.CURRENT_USER, `Software\Microsoft\Windows\CurrentVersion\Run`, registry.SET_VALUE)
	if err != nil {
		return
	}
	defer k.Close()
	if on {
		exe, _ := os.Executable()
		_ = k.SetStringValue("Raabt", `"`+exe+`"`)
	} else {
		_ = k.DeleteValue("Raabt")
	}
}
