<div align="center">
  <h1>📷 Xuying Photo Toolkit</h1>
  <p>Bring organize, pair, and sync capabilities to your photography workflow.</p>
  <p>Rename photos by capture time, clean unmatched RAW/JPG files, and sync Adobe Bridge stars and color labels from one focused macOS app.</p>
  <p>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/xuying-studio/xuying-photo-toolkit?style=flat-square" alt="MIT License"></a>
    <img src="https://img.shields.io/badge/macOS-11%2B-000000?style=flat-square&amp;logo=apple" alt="macOS 11+">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.10+">
  </p>
  <p><img src="assets/app_icon.png" width="144" alt="Xuying Photo Toolkit app icon"></p>
  <p>
    <a href="#quick-start">Quick Start</a> ·
    <a href="#what-it-does">Features</a> ·
    <a href="#before-you-start">Safety</a> ·
    <a href="docs/使用说明.md">Full Guide</a> ·
    <a href="#build-from-source">Build</a> ·
    <a href="CONTRIBUTING.md">Contributing</a> ·
    <a href="#license">License</a>
  </p>
  <p>
    <a href="README.md">中文</a> ·
    <a href="README.en.md">English</a> ·
    <a href="README.ja.md">日本語</a> ·
    <a href="README.es.md">Español</a> ·
    <a href="README.ko.md">한국어</a> ·
    <a href="README.ar.md">العربية</a>
  </p>
</div>

---

<a id="why"></a>

## Why do you need it?

After a shoot, the most tedious tasks are often the ones that should not be handled manually:

- 📁 RAW, JPG, and XMP sidecars are scattered across nested folders and need one capture-date-based naming scheme.
- 🧹 Exports or transfers leave unmatched JPG or RAW files behind, but bulk deletion feels risky.
- ⭐ Adobe Bridge selections need to be copied back and forth between JPG and RAW files.
- 🛡️ Batch processing is useful only when name collisions, accidental deletion, and rollback are handled clearly.

Xuying Photo Toolkit turns the workflow into: **scan and preview → review the counts → confirm and execute → undo when needed**.

---

<a id="what-it-does"></a>

## ✨ What does it do?

| Feature | Use it when | File protection |
| --- | --- | --- |
| 🕒 Rename by capture time | You want consistent names for RAW, JPG, and XMP sidecars | Preview first, block conflicts, two-phase rename, undo support |
| 🧹 RAW / JPG pair cleanup | You want to find files without a same-name pair | Move to macOS Trash and create a safety recovery copy |
| ⭐ Star and color sync | You want Adobe Bridge marks copied between matching RAW/JPG files | RAW files receive only `.xmp`; targets are backed up and reversible |

Every page scans the selected folder recursively by default and shows the total photos, pair status, and actual pending count before execution.

> No command memorization is required, and no photo is modified before you confirm an operation.

---

<a id="before-you-start"></a>

## ✅ Before you start

| Concern | Behavior |
| --- | --- |
| 🔒 Privacy | Photos, paths, and metadata stay on your Mac. The app has no photo upload or sync feature. |
| 👀 Preview first | All three workflows scan and show a list and statistics before changes are made. |
| 🛡️ No overwrites | Existing target names and rename conflicts stop the operation instead of silently overwriting. |
| 🗑️ No permanent deletion | Pair cleanup moves files to macOS Trash and keeps a local safety copy. |
| ↩️ Undo | Rename, cleanup recovery, and XMP sync retain the most recent recovery path. |
| 📷 RAW-safe | RAW originals are never written directly; metadata uses an `.xmp` sidecar. |

> ⚠️ This is a batch file tool, not a backup system. Test with a small copy of a project first.

---

<a id="quick-start"></a>

## 🚀 Quick Start

### Use the macOS App

1. Download the `.dmg` from the [Releases page](https://github.com/xuying-studio/xuying-photo-toolkit/releases).
2. Open it and drag `旭影的摄影工具集.app` into Applications.
3. Open the app, choose a photo folder, and click **Scan and Preview** first.

> The current release uses a local ad-hoc signature and is not notarized with an Apple Developer ID. On another Mac, the first launch may require right-clicking the app and choosing **Open**.

### Run from source

Requirements: macOS 11 or later, Python 3.10 or later, and the Tkinter provided by macOS/Python.

```bash
git clone https://github.com/xuying-studio/xuying-photo-toolkit.git
cd xuying-photo-toolkit
python3 -m pip install -r requirements.txt
python3 main.py
```

### A safe first run

1. Copy a small RAW/JPG sample into a test folder.
2. Select a feature page and click **Scan and Preview**.
3. Review the statistics and pending list.
4. Execute and inspect the result.
5. Process the full project only after the sample behaves as expected.

For supported formats, naming rules, recovery behavior, and troubleshooting, read the [full guide](docs/使用说明.md).

---

<a id="how-to-use"></a>

## 🧭 How the three workflows work

### 🕒 Rename by capture time

The app prefers EXIF capture time and falls back to file modification time. The output looks like this:

```text
DSC26-07-25-00001.arw
DSC26-07-25-00001.jpg
DSC26-07-25-00001.xmp
```

Matching RAW sidecars are renamed together. Files already using this format stay unchanged, and numbering continues after the highest existing number for that date.

### 🧹 RAW / JPG pair cleanup

Pairing happens in the **same folder**, using the same filename stem and case-insensitive matching:

```text
A001.JPG  ↔  a001.ARW
```

Choose either **JPG without RAW** or **RAW without JPG**. Files go to macOS Trash rather than being permanently deleted. Recovery first uses the hidden safety copy and falls back to Finder when necessary.

### ⭐ Adobe Bridge star and color sync

Both directions are supported: `JPG → RAW` and `RAW → JPG`. You can sync stars, color labels, or both.

- Writing to RAW creates or updates only its `.xmp` sidecar.
- Writing to JPG creates a complete backup before updating embedded XMP.
- If one item in a batch fails, already-processed targets are restored automatically.

---

<a id="appearance-and-data"></a>

## 🎨 Appearance and local data

The app follows the macOS light/dark appearance. The **Appearance…** control supports live opacity from 70% to 100%, with a default of 92%.

The new configuration path is:

```text
~/Library/Application Support/旭影的摄影工具集/ui_config.json
```

For compatibility with previous undo records, business backup folders keep their historical Chinese name. See the [local data section of the full guide](docs/使用说明.md#8-本地数据与隐私).

---

<a id="build-from-source"></a>

## 🧰 Build from source

```bash
chmod +x build_app.sh
./build_app.sh
```

The script runs the full test suite and then creates universal macOS artifacts for Apple Silicon and Intel:

- `dist/旭影的摄影工具集.app`
- `dist/旭影的摄影工具集-macOS-universal.zip`
- `dist/旭影的摄影工具集-macOS-universal.dmg`

The default build uses ad-hoc signing. For distribution without the first-launch warning, provide an Apple Developer ID Application certificate and a `notarytool` profile:

```bash
APPLE_SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" \
APPLE_NOTARY_PROFILE="your-notarytool-profile" \
./build_app.sh
```

---

## 📦 Historical standalone scripts

The repository keeps the three original standalone scripts for reference:

- `根据时间重命名文件排序.py`
- `根据RAW:JPG双向同步.py`
- `同步颜色与星号标记.py`

For daily use, prefer `main.py` or the macOS app. The unified app adds recursive scan statistics, conflict protection, and more complete undo handling.

---

## 🤝 Contributing and feedback

- Read [CONTRIBUTING.md](CONTRIBUTING.md) before sending a change.
- Open an [Issue](https://github.com/xuying-studio/xuying-photo-toolkit/issues) for bugs and feature requests.
- For possible overwrite, data-loss, or disclosure issues, follow [SECURITY.md](SECURITY.md) and report privately.

Do not upload real photos, complete personal paths, Trash records, or private EXIF/XMP data to an Issue.

---

<a id="license"></a>

## 📄 License

[MIT License](LICENSE) © 2026 旭影
