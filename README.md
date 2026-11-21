<p align="center">
  <img src="icon.png" width="96" alt="Fiş Yazıcı icon">
</p>

<h1 align="center">Fiş Yazıcı — Thermal Receipt Printer App</h1>

<p align="center">
  A desktop app for cheap Bluetooth mini thermal printers: design a receipt, preview it, print it.<br>
  <b>Windows · macOS · Linux</b><br>
  <sub>Python · CustomTkinter · Bleak (BLE) · Pillow</sub>
</p>

> **Note:** The app's user interface is in Turkish ("Fiş Yazıcı" means "Receipt Printer").
> This README explains every control in English.

---

## Features

- **Block-based receipt editor.** A receipt is a stack of text, photo, line and spacer blocks that you can reorder, duplicate and delete.
- **Live preview.** Shows exactly what will come out of the printer (384 px wide, black and white).
- **Text.** 6 fonts, 10–120 px size, left/center/right alignment, bold, and inverted (white on black). The `{tarih}` (date) and `{saat}` (time) placeholders are filled in at print time.
- **Photos.**
  - Width, brightness, contrast and alignment controls.
  - Photo mode: grayscale is converted to dots with Floyd–Steinberg dithering.
  - **Portrait / Landscape orientation.** In landscape mode the photo is rotated 90° and printed along the length of the receipt. This is ideal for panoramas and wide screenshots.
- **Print settings.** 4 darkness levels, multiple copies, paper feed, and a `Ctrl+P` shortcut (`⌘P` on macOS).
- **Connection monitoring.** The connection is checked continuously and shown as connected, not responding, or lost. The app can optionally connect automatically on start.
- **Templates.** Receipts can be saved and opened as JSON. The last receipt is saved automatically. Example: [`ornek_market_fisi.json`](ornek_market_fisi.json) (a sample grocery receipt).
- **Theme.** Light, dark, or follow the system.

## Supported printers

The app speaks the `51 78 …` BLE packet protocol used by most cheap mini thermal printers (often called the "cat printer" protocol). The printer must have a **384-pixel print width** (about 48 mm on 58 mm paper).

| Model | Status |
|---|---|
| **X5h** | ✅ Tested, fully supported |
| **X5** and other models whose Bluetooth name starts with `X5` | ✅ Found automatically, same protocol |
| GB01, GB02, GB03, GT01, MX05, MX06, MX08, MX10, YT01 | ⚠️ Same protocol family, **not tested** (see below) |

**Untested models:** The Bluetooth scan only looks for devices whose name starts with `X5`. To try another model, change `NAME_PREFIX` in [`printer.py`](printer.py) to match your printer's Bluetooth name (for example `"GB0"` or `"MX"`). On Windows and Linux you can also put your printer's MAC address in `DEFAULT_ADDRESS`. Some models in this family use a different print width or slightly different commands. If the result looks wrong, try a different darkness level.

**Not compatible:** classic ESC/POS USB or serial receipt printers (Epson TM series, etc.), and printers with their own protocols such as the Phomemo M02 or Peripage.

## Supported operating systems

| OS | Version | Bluetooth backend | Status |
|---|---|---|---|
| **Windows** | 10 (1709+) or 11 | WinRT | ✅ Tested with a real printer |
| **Linux** | Distributions with BlueZ 5.55+ (Ubuntu 22.04+, Debian 12+, Fedora 36+, Arch, …) | BlueZ (D-Bus) | ⚠️ App tested on Ubuntu 24.04, printing not yet tested |
| **macOS** | 11 Big Sur or later (Intel and Apple Silicon) | CoreBluetooth | ⚠️ Supported, not tested |

Requirements on every OS:

- A **Bluetooth Low Energy** (BLE, Bluetooth 4.0+) adapter, built in or USB.
- **Python 3.10 or later** (developed with 3.12), with Tkinter.

All three systems use the [Bleak](https://github.com/hbldh/bleak) library for Bluetooth. Receipt fonts are looked up in each system's own font folders. On Linux, if Microsoft fonts are missing, metric-compatible open-source fonts (Liberation, DejaVu) are used instead.

## Installation

### Windows

```powershell
git clone https://github.com/ByFalcony/thermal-printer-application.git
cd thermal-printer-application
python -m pip install -r requirements.txt
```

**Run:** Double-click `Baslat.bat`. It installs missing packages first, then opens the app without a console window. You can also run `python app.py`.

**Shortcut (optional):** To add an app shortcut with its icon to the Desktop and the Start menu:

```powershell
python -m pip install pywin32
python kisayol_olustur.py
```

### macOS

Installing Python from [python.org](https://www.python.org/downloads/macos/) is recommended because it includes Tkinter. With Homebrew, use `brew install python python-tk`.

```bash
git clone https://github.com/ByFalcony/thermal-printer-application.git
cd thermal-printer-application
./baslat.sh
```

On the first run, a virtual environment (`.venv`) is created in the project folder and the packages are installed. Later runs start immediately. To start from Finder, double-click `Baslat.command`.

**Bluetooth permission:** The first time the app connects, macOS asks whether the program that launched it (Terminal, iTerm, etc.) may use Bluetooth. Allow it. You can change this later under *System Settings → Privacy & Security → Bluetooth*.

**Shortcut (optional):** Creates a `Fiş Yazıcı.app` bundle in `~/Applications` that shows up in Launchpad and Spotlight:

```bash
.venv/bin/python kisayol_olustur.py
```

### Linux

Install the system packages first:

```bash
# Debian / Ubuntu / Mint
sudo apt install python3 python3-venv python3-tk bluez fonts-liberation

# Fedora
sudo dnf install python3 python3-tkinter bluez liberation-fonts

# Arch
sudo pacman -S python tk bluez bluez-utils ttf-liberation
```

Make sure the Bluetooth service is running: `sudo systemctl enable --now bluetooth`

Then:

```bash
git clone https://github.com/ByFalcony/thermal-printer-application.git
cd thermal-printer-application
./baslat.sh
```

On the first run, a virtual environment (`.venv`) is created in the project folder and the packages are installed.

**Shortcut (optional):** Adds a `.desktop` launcher to the application menu and the desktop:

```bash
.venv/bin/python kisayol_olustur.py
```

## Usage

1. Turn on the printer. **Make sure it is not connected to the printer app on your phone.** BLE printers accept only one connection at a time.
2. Press **Bağlan** (Connect). If **Otomatik bağlan** (Auto-connect) is on, the app connects by itself on start.
3. Add blocks from the **Ekle** (Add) section on the left: **Metin** (Text), **Fotoğraf** (Photo), **Çizgi** (Line), **Boşluk** (Space). Edit the selected block in the middle panel.
4. Check the preview on the right, choose **Koyuluk** (Darkness) and **Kopya** (Copies), and press **Yazdır** (Print).

**Interface glossary**

| Turkish | English |
|---|---|
| Yeni / Aç / Kaydet | New / Open / Save |
| Açık / Koyu / Sistem | Light / Dark / System (theme) |
| Bağlan / Bağlantıyı kes | Connect / Disconnect |
| Fiş içeriği | Receipt content (block list) |
| Çoğalt / Sil | Duplicate / Delete |
| Yazı tipi, Boyut, Hizalama, Kalın, Ters renk | Font, Size, Alignment, Bold, Inverted |
| Genişlik, Parlaklık, Kontrast | Width, Brightness, Contrast |
| Yön: Dikey / Yatay | Orientation: Portrait / Landscape |
| Fotoğraf modu | Photo mode (dithering) |
| Çizgi tipi: Düz / Kesikli, Kalınlık | Line style: Solid / Dashed, Thickness |
| Yükseklik | Height |
| Koyuluk: Açık / Normal / Koyu / Çok koyu | Darkness: Light / Normal / Dark / Very dark |
| Kağıt ilerlet | Feed paper |
| Önizleme | Preview |

**Tips**

- For logos or images that contain text, turning *photo mode* off gives sharper results.
- If photos print too faint, increase the contrast or set the darkness to *Koyu* (Dark).
- 8 px is about 1 mm of paper.

## Project structure

```
app.py                 User interface (CustomTkinter)
printer.py             BLE printer driver (runs in a background asyncio thread)
render.py              Turns blocks into a 384 px black-and-white image and printer rows
make_icon.py           Generates icon.png / icon.ico
kisayol_olustur.py     Creates a shortcut (Windows .lnk, macOS .app, Linux .desktop)
ornek_market_fisi.json Sample template
Baslat.bat             Windows launcher
baslat.sh              Linux / macOS launcher (sets up its own virtual environment)
Baslat.command         macOS launcher you can double-click in Finder
```

The files `son_fis.json` (last receipt) and `ayarlar.json` (user settings) are created at runtime. They are personal and are not committed to the repository.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Bluetooth taraması başarısız" (Bluetooth scan failed) | Check that Bluetooth is turned on. On Linux, check the service with `systemctl status bluetooth`. |
| "Yazıcı bulunamadı" (Printer not found) | Check that the printer is on and not connected to your phone. If your model's name does not start with `X5`, see the `NAME_PREFIX` note above. |
| Printer is never found on macOS | Check that Terminal has Bluetooth permission (*System Settings → Privacy & Security → Bluetooth*). |
| "Yanıt yok" (Not responding) | The printer may be out of range or asleep. Disconnect and connect again. |
| "Tkinter eksik" (Tkinter missing) on Linux | Install `python3-tk` (Debian/Ubuntu), `python3-tkinter` (Fedora) or `tk` (Arch). |
| `externally-managed-environment` error on Linux | Don't install with `pip` into the system Python. Use the `.venv` that `./baslat.sh` creates. |
| Receipt fonts look different | If a font is missing on the system, the closest match is used. On Linux, install `fonts-liberation`. |
| Faint print | Increase the darkness. For photos, also raise the contrast. |
