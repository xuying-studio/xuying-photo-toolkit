<div align="center">
  <h1>📷 旭影の写真ツールキット</h1>
  <p>写真ワークフローに「整理・ペア確認・同期」を追加します。</p>
  <p>撮影日時によるリネーム、RAW/JPG のペア整理、Adobe Bridge の星評価とカラーラベル同期を、ひとつの macOS アプリにまとめました。</p>
  <p>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/xuying-studio/xuying-photo-toolkit?style=flat-square" alt="MIT License"></a>
    <img src="https://img.shields.io/badge/macOS-11%2B-000000?style=flat-square&amp;logo=apple" alt="macOS 11+">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.10+">
  </p>
  <p><img src="assets/app_icon.png" width="144" alt="旭影の写真ツールキットのアイコン"></p>
  <p>
    <a href="#quick-start">クイックスタート</a> ·
    <a href="#features">機能</a> ·
    <a href="#safety">安全性</a> ·
    <a href="docs/使用说明.md">詳細ガイド</a> ·
    <a href="#build">ビルド</a> ·
    <a href="CONTRIBUTING.md">コントリビュート</a> ·
    <a href="#license">ライセンス</a>
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

## なぜ必要ですか？

撮影後に発生する、手作業では間違いやすい整理作業をまとめて安全に処理できます。

- 📁 RAW、JPG、XMP サイドカーが複数のフォルダに分散し、撮影日順に名前を統一したい。
- 🧹 書き出しやコピーの後に、対応する RAW/JPG がないファイルが残ってしまう。
- ⭐ Adobe Bridge で付けた星評価やカラーラベルを JPG と RAW の間で同期したい。
- 🛡️ 一括処理したいが、上書き・誤削除・取り消し不能な変更は避けたい。

旭影の写真ツールキットは、**スキャンとプレビュー → 件数を確認 → 承認して実行 → 必要なら取り消し**という流れに固定します。

---

<a id="features"></a>

## ✨ できること

| 機能 | 使う場面 | ファイル保護 |
| --- | --- | --- |
| 🕒 撮影日時でリネーム | RAW、JPG、XMP サイドカーの名前を統一したいとき | 事前プレビュー、競合停止、二段階リネーム、取り消し |
| 🧹 RAW / JPG ペア整理 | 同名の対応ファイルがない写真を探したいとき | macOS のゴミ箱へ移動し、安全な復元コピーを作成 |
| ⭐ 星評価とカラー同期 | 対応する RAW/JPG 間で Adobe Bridge の情報を移したいとき | RAW は `.xmp` のみ更新、対象をバックアップして取り消し可能 |

すべてのページは、選択したフォルダ以下を標準で再帰スキャンし、実行前に総数・ペア状況・処理対象数を表示します。

> コマンドを覚える必要はありません。「実行」を確認するまで写真は変更されません。

---

<a id="safety"></a>

## ✅ 使う前に知っておきたいこと

| 項目 | 動作 |
| --- | --- |
| 🔒 プライバシー | 写真、パス、メタデータは Mac 上だけで処理します。写真をアップロード・同期する機能はありません。 |
| 👀 先にプレビュー | 3 つの機能すべてで、変更前に一覧と統計を確認できます。 |
| 🛡️ 上書きしない | 既存の対象名やリネーム競合がある場合、処理を停止します。 |
| 🗑️ 完全削除しない | ペア整理では macOS のゴミ箱へ移動し、安全な復元コピーを保持します。 |
| ↩️ 取り消し | リネーム、整理の復元、XMP 同期には直近の復元手段があります。 |
| 📷 RAW を保護 | RAW 本体には直接書き込まず、メタデータは `.xmp` サイドカーに保存します。 |

> ⚠️ バックアップソフトではありません。最初はプロジェクトのコピーで動作を確認してください。

---

<a id="quick-start"></a>

## 🚀 クイックスタート

### macOS App を使う

1. [Releases](https://github.com/xuying-studio/xuying-photo-toolkit/releases) から `.dmg` をダウンロードします。
2. DMG を開き、「旭影的摄影工具集.app」を「アプリケーション」へドラッグします。
3. App を開き、写真フォルダを選択して、まず「スキャンしてプレビュー」を実行します。

> 現在のリリースはローカル ad-hoc 署名で、Apple Developer ID の公証は受けていません。他の Mac で初めて開く場合は、App を右クリックして「開く」を選ぶ必要があります。

### ソースから実行

要件：macOS 11 以降、Python 3.10 以降、macOS/Python に付属する Tkinter。

```bash
git clone https://github.com/xuying-studio/xuying-photo-toolkit.git
cd xuying-photo-toolkit
python3 -m pip install -r requirements.txt
python3 main.py
```

### 初回は小さく試す

1. RAW/JPG の小さなコピーをテストフォルダに用意します。
2. 機能ページを選び、「スキャンしてプレビュー」を押します。
3. 統計と対象一覧を確認します。
4. 実行後、結果を確認します。
5. 問題がなければ本番プロジェクトを処理します。

対応形式、命名規則、復元動作、トラブルシューティングは[詳細ガイド](docs/使用说明.md)をご覧ください。

---

<a id="workflows"></a>

## 🧭 3 つの機能の使い方

### 🕒 撮影日時でリネーム

EXIF の撮影日時を優先し、読めない場合はファイルの更新日時を使います。

```text
DSC26-07-25-00001.arw
DSC26-07-25-00001.jpg
DSC26-07-25-00001.xmp
```

対応する RAW のサイドカーも一緒にリネームします。すでにこの形式のファイルは変更せず、その日の最大番号から続けます。

### 🧹 RAW / JPG ペア整理

**同じフォルダ内**で、拡張子を除いた名前を大文字小文字を区別せず比較します。

```text
A001.JPG  ↔  a001.ARW
```

「RAW がない JPG」または「JPG がない RAW」を選べます。ファイルは完全削除せずゴミ箱へ移動します。復元時は安全コピーを優先し、必要な場合のみ Finder を使います。

### ⭐ Adobe Bridge の星評価とカラー同期

`JPG → RAW` と `RAW → JPG` の両方向に対応しています。星評価、カラーラベル、または両方を選択できます。

- RAW へ書き込む場合は `.xmp` サイドカーだけを作成・更新します。
- JPG へ書き込む場合は、内蔵 XMP を更新する前に完全バックアップを作成します。
- バッチ中に失敗した場合、処理済みの対象を自動的に復元します。

---

<a id="appearance"></a>

## 🎨 外観とローカルデータ

macOS のライト/ダーク外観に追従します。「外観…」から透明度を 70%–100% の範囲でリアルタイム調整できます。初期値は 92% です。

設定ファイル：

```text
~/Library/Application Support/旭影的摄影工具集/ui_config.json
```

旧バージョンの取り消し記録との互換性のため、業務バックアップフォルダには旧名称が残ります。詳しくは[詳細ガイドのローカルデータ章](docs/使用说明.md#8-本地数据与隐私)をご覧ください。

---

<a id="build"></a>

## 🧰 ソースからビルド

```bash
chmod +x build_app.sh
./build_app.sh
```

スクリプトは全テストを実行した後、Apple Silicon と Intel の両方に対応する App、ZIP、DMG を生成します。

デフォルトは ad-hoc 署名です。公証済み配布には Apple Developer ID Application 証明書と `notarytool` プロファイルを設定してください。

---

## 📦 旧スタンドアロンスクリプト

追跡と参考のため、最初の 3 つのスクリプトもリポジトリに残しています。

- `根据时间重命名文件排序.py`
- `根据RAW:JPG双向同步.py`
- `同步颜色与星号标记.py`

日常利用では `main.py` または macOS App を推奨します。

---

## 🤝 コントリビュートとフィードバック

- 変更を送る前に [CONTRIBUTING.md](CONTRIBUTING.md) を確認してください。
- バグや機能提案は [Issue](https://github.com/xuying-studio/xuying-photo-toolkit/issues) へ。
- 上書き、データ損失、情報漏えいにつながる可能性がある問題は [SECURITY.md](SECURITY.md) に従って非公開で報告してください。

Issue に実際の写真、完全な個人パス、ゴミ箱の記録、個人情報を含む EXIF/XMP をアップロードしないでください。

---

<a id="license"></a>

## 📄 ライセンス

[MIT License](LICENSE) © 2026 旭影
