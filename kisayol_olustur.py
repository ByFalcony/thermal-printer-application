"""Simgeli 'Fiş Yazıcı' kısayolu oluşturur.

Windows: Masaüstü ve Başlat menüsünde .lnk kısayolu. Kısayol, uygulamayla aynı
         AppUserModelID'yi taşır; görev çubuğuna sabitlendiğinde de uygulamanın
         simgesi görünür. Gerekli: pip install pywin32
Linux:   ~/.local/share/applications içine .desktop girdisi (uygulama menüsü)
         ve varsa masaüstüne bir kopyası.
macOS:   ~/Applications içine 'Fiş Yazıcı.app' paketi (Launchpad / Spotlight).
"""
import os
import plistlib
import shlex
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ID = "Emir.FisYazici.1"   # app.py içindeki APP_ID ile aynı olmalı
NAME = "Fiş Yazıcı"
DESCRIPTION = "Mini termal yazıcı için fiş tasarlama ve yazdırma"


# ---------------------------------------------------------------- Windows
def pythonw_path():
    exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return exe if os.path.exists(exe) else sys.executable


def make_windows_shortcut(folder):
    import pythoncom
    from win32com.client import Dispatch
    from win32com.propsys import propsys, pscon
    from win32com.shell import shellcon

    path = os.path.join(folder, NAME + ".lnk")
    sc = Dispatch("WScript.Shell").CreateShortcut(path)
    sc.TargetPath = pythonw_path()
    sc.Arguments = f'"{os.path.join(HERE, "app.py")}"'
    sc.WorkingDirectory = HERE
    sc.IconLocation = os.path.join(HERE, "icon.ico") + ",0"
    sc.Description = DESCRIPTION
    sc.Save()

    store = propsys.SHGetPropertyStoreFromParsingName(path, None, shellcon.GPS_READWRITE,
                                                      propsys.IID_IPropertyStore)
    store.SetValue(pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(APP_ID, pythoncom.VT_LPWSTR))
    store.Commit()
    return path


def windows():
    try:
        from win32com.shell import shell, shellcon
    except ImportError:
        sys.exit("pywin32 gerekli:  python -m pip install pywin32")
    desktop = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, None, 0)
    programs = shell.SHGetFolderPath(0, shellcon.CSIDL_PROGRAMS, None, 0)
    return [make_windows_shortcut(f) for f in (desktop, programs)]


# ---------------------------------------------------------------- ortak (Linux / macOS)
def _make_executable(path):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _launcher():
    launcher = os.path.join(HERE, "baslat.sh")
    _make_executable(launcher)
    return launcher


# ---------------------------------------------------------------- Linux
def _desktop_quote(path):
    """.desktop dosyasının Exec= alanı için çift tırnaklı yol (freedesktop kuralları)."""
    esc = path.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    return f'"{esc}"'


def _desktop_dir():
    """XDG masaüstü klasörü (Türkçe sistemlerde 'Masaüstü' olabilir)."""
    try:
        import subprocess
        out = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, timeout=5)
        path = out.stdout.strip()
        if path and os.path.isdir(path) and path != os.path.expanduser("~"):
            return path
    except Exception:
        pass
    for name in ("Desktop", "Masaüstü"):
        p = os.path.join(os.path.expanduser("~"), name)
        if os.path.isdir(p):
            return p
    return None


def linux():
    entry = "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        f"Name={NAME}",
        f"Comment={DESCRIPTION}",
        f"Exec={_desktop_quote(_launcher())}",
        f"Path={HERE}",
        f"Icon={os.path.join(HERE, 'icon.png')}",
        "Terminal=false",
        "Categories=Utility;Office;",
        "",
    ])
    apps = os.path.join(os.path.expanduser("~"), ".local", "share", "applications")
    os.makedirs(apps, exist_ok=True)
    targets = [os.path.join(apps, "fis-yazici.desktop")]
    desktop = _desktop_dir()
    if desktop:
        targets.append(os.path.join(desktop, "fis-yazici.desktop"))
    for t in targets:
        with open(t, "w", encoding="utf-8") as f:
            f.write(entry)
        _make_executable(t)
    if desktop:
        print("Not: Masaüstündeki kısayolu ilk açışta sağ tıklayıp 'Başlatmaya izin ver' "
              "(Allow Launching) seçmeniz gerekebilir.")
    return targets


# ---------------------------------------------------------------- macOS
def macos():
    app = os.path.join(os.path.expanduser("~"), "Applications", NAME + ".app")
    contents = os.path.join(app, "Contents")
    macos_dir = os.path.join(contents, "MacOS")
    res = os.path.join(contents, "Resources")
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(res, exist_ok=True)

    exe = os.path.join(macos_dir, "FisYazici")
    with open(exe, "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env bash\n"
                "# Finder'dan açılan uygulamalar kısıtlı PATH alır; Homebrew ve python.org yollarını ekle\n"
                'export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/'
                'Versions/Current/bin:$PATH"\n'
                f"exec {shlex.quote(_launcher())}\n")
    _make_executable(exe)

    try:
        from PIL import Image
        Image.open(os.path.join(HERE, "icon.png")).save(os.path.join(res, "icon.icns"))
    except Exception as e:
        print("Simge oluşturulamadı:", e)

    info = {
        "CFBundleName": NAME,
        "CFBundleDisplayName": NAME,
        "CFBundleIdentifier": "com.byfalcony.fisyazici",
        "CFBundleVersion": "1.0",
        "CFBundlePackageType": "APPL",
        "CFBundleExecutable": "FisYazici",
        "CFBundleIconFile": "icon.icns",
        "NSHighResolutionCapable": True,
        "NSBluetoothAlwaysUsageDescription": "Fiş Yazıcı, termal yazıcıya Bluetooth ile bağlanır.",
    }
    with open(os.path.join(contents, "Info.plist"), "wb") as f:
        plistlib.dump(info, f)
    print("Not: İlk açılışta paketler kurulurken birkaç dakika beklemek gerekebilir. "
          "Önce Terminal'de bir kez ./baslat.sh çalıştırmanız önerilir.")
    return [app]


def main():
    if sys.platform == "win32":
        made = windows()
    elif sys.platform == "darwin":
        made = macos()
    else:
        made = linux()
    for p in made:
        print("Oluşturuldu:", p)


if __name__ == "__main__":
    main()
