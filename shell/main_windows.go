//go:build windows

package main

import (
	_ "embed"
	"encoding/base64"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"unsafe"

	"github.com/jchv/go-webview2"
	"golang.org/x/sys/windows"
	"golang.org/x/sys/windows/registry"
)

//go:embed ui.html
var uiHTML string

//go:embed raabt.wasm
var coreWasm []byte

//go:embed logo.png
var logoPNG []byte

var pMessageBox = windows.NewLazySystemDLL("user32.dll").NewProc("MessageBoxW")

func msgBox(title, text string) {
	t, _ := windows.UTF16PtrFromString(title)
	x, _ := windows.UTF16PtrFromString(text)
	pMessageBox.Call(0, uintptr(unsafe.Pointer(x)), uintptr(unsafe.Pointer(t)), 0x40|0x00100000)
}

// dataDir: everything lives in a folder beside the exe (portable).
func dataDir() string {
	exe, _ := os.Executable()
	d := filepath.Join(filepath.Dir(exe), "Raabt-data")
	_ = os.MkdirAll(d, 0o755)
	return d
}

func webview2Installed() bool {
	const guid = `{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`
	for _, p := range []struct {
		root registry.Key
		key  string
	}{
		{registry.LOCAL_MACHINE, `SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\` + guid},
		{registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\EdgeUpdate\Clients\` + guid},
		{registry.CURRENT_USER, `Software\Microsoft\EdgeUpdate\Clients\` + guid},
	} {
		k, err := registry.OpenKey(p.root, p.key, registry.QUERY_VALUE)
		if err != nil {
			continue
		}
		v, _, err := k.GetStringValue("pv")
		k.Close()
		if err == nil && v != "" && v != "0.0.0.0" {
			return true
		}
	}
	return false
}

var wv webview2.WebView

var (
	pFindWindow = windows.NewLazySystemDLL("user32.dll").NewProc("FindWindowW")
	pShowWin    = windows.NewLazySystemDLL("user32.dll").NewProc("ShowWindow")
	pSetFg      = windows.NewLazySystemDLL("user32.dll").NewProc("SetForegroundWindow")
)

// singleInstance: a second launch from the same folder brings the first window forward instead of
// opening a second copy that would overwrite the same data files.
func singleInstance() bool {
	exe, _ := os.Executable()
	var h uint32 = 2166136261
	for _, c := range []byte(strings.ToLower(filepath.Dir(exe))) {
		h = (h ^ uint32(c)) * 16777619
	}
	name, _ := windows.UTF16PtrFromString("Local\\Raabt-" + strconv.FormatUint(uint64(h), 16))
	_, err := windows.CreateMutex(nil, false, name)
	if err == windows.ERROR_ALREADY_EXISTS {
		t, _ := windows.UTF16PtrFromString("راابط")
		if hw, _, _ := pFindWindow.Call(0, uintptr(unsafe.Pointer(t))); hw != 0 {
			pShowWin.Call(hw, 9)
			pSetFg.Call(hw)
		}
		return false
	}
	return true
}

func main() {
	if !webview2Installed() {
		msgBox("راابط", "مكوّن WebView2 مش موجود على الجهاز. نزّله من مايكروسوفت (Microsoft Edge WebView2 Runtime) وافتح راابط تاني.\n\nWebView2 Runtime was not found. Install it from Microsoft and run Raabt again.")
		return
	}
	if !singleInstance() {
		return
	}
	if !dirWritable(dataDir()) {
		msgBox("راابط", "مش قادر أكتب جنب البرنامج. انقل راابط لفولدر عادي (زي Desktop أو Documents) وافتحه تاني.\n\nRaabt cannot write beside the program. Move it to a normal folder (Desktop/Documents) and run again.")
		return
	}
	w := webview2.NewWithOptions(webview2.WebViewOptions{
		DataPath:      filepath.Join(dataDir(), "webview"),
		WindowOptions: webview2.WindowOptions{Title: "راابط", Width: 1100, Height: 760, Center: true, IconId: 3},
	})
	if w == nil {
		msgBox("راابط", "WebView2 مش شغال. WebView2 failed to start.")
		return
	}
	defer w.Destroy()
	w.Bind("rbLoad", func(name string) string { return loadFile(dataDir(), name) })
	w.Bind("rbSave", func(name, data string) bool { return saveFile(dataDir(), name, data) })
	w.Bind("rbSaveTo", func(dir, name, data string) bool { return saveFileTo(dir, name, data) })
	w.Bind("rbPickDir", func() string { return pickFolder("اختار مكان النسخ الاحتياطي") })
	w.Bind("rbOpen", func(u, browser string) {
		// No cmd.exe: ShellExecute passes the URL as one argument, so &, %, ^ in a URL cannot run commands.
		if !(strings.HasPrefix(u, "http://") || strings.HasPrefix(u, "https://")) || strings.ContainsAny(u, "\"\r\n ") {
			return
		}
		up, _ := windows.UTF16PtrFromString(u)
		op, _ := windows.UTF16PtrFromString("open")
		if exe, ok := browserExe[strings.ToLower(browser)]; ok {
			ep, _ := windows.UTF16PtrFromString(exe + ".exe")
			ap, _ := windows.UTF16PtrFromString("\"" + u + "\"")
			if windows.ShellExecute(0, op, ep, ap, nil, windows.SW_SHOWNORMAL) == nil {
				return
			}
		}
		_ = windows.ShellExecute(0, op, up, nil, nil, windows.SW_SHOWNORMAL)
	})
	w.Bind("rbMeta", func(u string) string { return fetchMeta(u) })
	w.Bind("rbCheck", func(u string) int { return checkURL(u) })
	w.Bind("rbExport", func(name, b64 string) string {
		p := exportFile(dataDir(), name, b64)
		if p != "" {
			exec.Command("explorer", "/select,", p).Start()
		}
		return p
	})
	wv = w
	initTray(uintptr(w.Window()))
	w.Bind("rbTray", func(on bool) { setTray(on) })
	w.Bind("rbHotkey", func(on bool, mods, vk int) bool { return setHotkey(on, uint32(mods), uint32(vk)) })
	w.Bind("rbBinWrite", func(sub, name, b64 string, first, last bool) bool { return binWrite(dataDir(), sub, name, b64, first, last) })
	w.Bind("rbBinSize", func(sub, name string) int { return int(binSize(dataDir(), sub, name)) })
	w.Bind("rbBinRead", func(sub, name string, off, n int) string { return binRead(dataDir(), sub, name, int64(off), int64(n)) })
	w.Bind("rbBinDel", func(sub, name string) bool { return binDel(dataDir(), sub, name) })
	w.Bind("rbMirror", func(mode string) int { return mirrorImages(dataDir(), mode) })
	w.Bind("rbFont", func(name string) string { return bundledFont(name) })
	w.Bind("rbArt", func(name string) string { return bundledArt(name) })
	w.Bind("rbPFont", func(name string) string { return personalFont(name) })
	w.Bind("rbAutostart", func(on bool) { setAutostart(on) })
	w.SetHtml(strings.Replace(strings.Replace(uiHTML, "{{WASM}}", base64.StdEncoding.EncodeToString(coreWasm), 1), "{{LOGO}}", "data:image/png;base64,"+base64.StdEncoding.EncodeToString(logoPNG), 1))
	w.Run()
}
