<div align="center">
  <h1>📷 쉬잉 사진 도구 모음</h1>
  <p>사진 작업 흐름에 정리, 페어 확인, 동기화 기능을 한 번에 더합니다.</p>
  <p>촬영 시간 기준 이름 변경, RAW/JPG 페어 정리, Adobe Bridge 별점과 색상 라벨 동기화를 하나의 macOS 앱으로 제공합니다.</p>
  <p>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/xuying-studio/xuying-photo-toolkit?style=flat-square" alt="MIT License"></a>
    <img src="https://img.shields.io/badge/macOS-11%2B-000000?style=flat-square&amp;logo=apple" alt="macOS 11+">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.10+">
  </p>
  <p><img src="assets/app_icon.png" width="144" alt="쉬잉 사진 도구 모음 아이콘"></p>
  <p>
    <a href="#quick-start">빠른 시작</a> ·
    <a href="#features">기능</a> ·
    <a href="#safety">안전성</a> ·
    <a href="docs/使用说明.md">전체 안내</a> ·
    <a href="#build">빌드</a> ·
    <a href="CONTRIBUTING.md">기여</a> ·
    <a href="#license">라이선스</a>
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

## 왜 필요한가요?

촬영 후 수작업으로 처리하기 쉽고 실수도 잦은 작업을 한곳에서 안전하게 처리합니다.

- 📁 여러 하위 폴더에 흩어진 RAW, JPG, XMP 사이드카의 이름을 촬영 날짜 기준으로 통일합니다.
- 🧹 내보내기나 복사 후 남은 짝 없는 JPG/RAW를 찾고 안전하게 정리합니다.
- ⭐ Adobe Bridge에서 지정한 별점과 색상 라벨을 JPG와 RAW 사이에 동기화합니다.
- 🛡️ 일괄 작업 중 이름 충돌, 실수로 인한 삭제, 되돌릴 수 없는 변경을 방지합니다.

쉬잉 사진 도구 모음은 흐름을 **스캔 및 미리 보기 → 수량 확인 → 확인 후 실행 → 필요하면 되돌리기**로 고정합니다.

---

<a id="features"></a>

## ✨ 어떤 기능이 있나요?

| 기능 | 사용하는 상황 | 파일 보호 방식 |
| --- | --- | --- |
| 🕒 촬영 시간 기준 이름 변경 | RAW, JPG, XMP 사이드카의 이름을 통일할 때 | 사전 미리 보기, 충돌 차단, 2단계 이름 변경, 되돌리기 |
| 🧹 RAW / JPG 페어 정리 | 같은 이름의 짝이 없는 파일을 찾을 때 | macOS 휴지통으로 이동하고 안전한 복구 사본 생성 |
| ⭐ 별점 및 색상 동기화 | 대응하는 RAW/JPG 사이에 Adobe Bridge 정보를 복사할 때 | RAW에는 `.xmp`만 쓰고 대상 파일을 백업하여 되돌릴 수 있음 |

모든 페이지는 선택한 폴더와 하위 폴더를 기본으로 재귀 스캔하며, 실행 전에 전체 사진 수, 페어 상태, 실제 처리 예정 수를 보여 줍니다.
스캔, 실행, 되돌리기 중에는 현재 수량, 전체 수량, 완료율이 실시간으로 표시됩니다.

> 명령어를 외울 필요가 없으며, 실행을 확인하기 전에는 사진을 변경하지 않습니다.

---

<a id="safety"></a>

## ✅ 사용 전에 알아둘 점

| 항목 | 동작 |
| --- | --- |
| 🔒 개인정보 보호 | 사진, 경로, 메타데이터는 Mac에서만 처리합니다. 사진을 업로드하거나 동기화하는 기능은 없습니다. |
| 👀 먼저 미리 보기 | 세 기능 모두 변경 전에 목록과 통계를 보여 줍니다. |
| 🛡️ 덮어쓰기 방지 | 대상 이름이 이미 있거나 충돌이 발생하면 조용히 덮어쓰지 않고 중단합니다. |
| 🗑️ 영구 삭제 없음 | 페어 정리는 macOS 휴지통으로 이동하고 로컬 복구 사본을 보관합니다. |
| ↩️ 되돌리기 | 이름 변경, 정리 복구, XMP 동기화에 최근 작업을 복구할 수 있는 경로가 있습니다. |
| 📷 RAW 보호 | RAW 원본에 직접 쓰지 않고 메타데이터를 `.xmp` 사이드카에 저장합니다. |

> ⚠️ 백업 프로그램이 아니라 일괄 파일 처리 도구입니다. 먼저 프로젝트 사본으로 테스트하세요.

---

<a id="quick-start"></a>

## 🚀 빠른 시작

### macOS 앱 사용

1. [Releases](https://github.com/xuying-studio/xuying-photo-toolkit/releases)에서 `.dmg`를 다운로드합니다.
2. DMG를 열고 `旭影的摄影工具集.app`을 응용 프로그램 폴더로 드래그합니다.
3. 앱을 열고 사진 폴더를 선택한 뒤 먼저 **스캔 및 미리 보기**를 클릭합니다.

> 현재 릴리스는 로컬 ad-hoc 서명만 되어 있으며 Apple Developer ID 공증을 받지 않았습니다. 다른 Mac에서 처음 실행할 때는 앱을 우클릭한 뒤 **열기**를 선택해야 할 수 있습니다.

### 소스에서 실행

요구 사항: macOS 11 이상, Python 3.10 이상, macOS/Python에서 제공하는 Tkinter.

```bash
git clone https://github.com/xuying-studio/xuying-photo-toolkit.git
cd xuying-photo-toolkit
python3 -m pip install -r requirements.txt
python3 main.py
```

### 안전한 첫 실행

1. 작은 RAW/JPG 사본을 테스트 폴더에 준비합니다.
2. 기능 페이지를 선택하고 **스캔 및 미리 보기**를 클릭합니다.
3. 통계와 처리 예정 목록을 확인합니다.
4. 실행한 뒤 결과를 확인합니다.
5. 샘플이 정상일 때 전체 프로젝트를 처리합니다.

지원 형식, 이름 규칙, 복구 동작, 문제 해결은 [전체 안내](docs/使用说明.md)를 참고하세요.

---

<a id="workflows"></a>

## 🧭 세 가지 기능 사용법

### 🕒 촬영 시간 기준 이름 변경

EXIF 촬영 시간을 우선 사용하고, 읽을 수 없으면 파일 수정 시간을 사용합니다.

```text
DSC26-07-25-00001.arw
DSC26-07-25-00001.jpg
DSC26-07-25-00001.xmp
```

대응하는 RAW 사이드카도 함께 이름을 변경합니다. 이미 이 형식인 파일은 유지하며, 해당 날짜의 가장 큰 번호 다음부터 계속합니다.

### 🧹 RAW / JPG 페어 정리

**같은 폴더 안에서** 확장자를 제외한 이름을 대소문자 구분 없이 비교합니다.

```text
A001.JPG  ↔  a001.ARW
```

**RAW가 없는 JPG** 또는 **JPG가 없는 RAW**를 선택할 수 있습니다. 파일은 영구 삭제되지 않고 macOS 휴지통으로 이동합니다. 복구할 때는 숨겨진 안전 사본을 먼저 사용하고 필요한 경우에만 Finder를 사용합니다.

### ⭐ Adobe Bridge 별점 및 색상 동기화

`JPG → RAW`, `RAW → JPG` 두 방향을 지원합니다. 별점, 색상 라벨 또는 둘 다 선택할 수 있습니다.

- RAW에 쓸 때는 `.xmp` 사이드카만 생성하거나 업데이트합니다.
- JPG에 쓸 때는 내장 XMP를 업데이트하기 전에 전체 백업을 만듭니다.
- 일괄 작업 중 하나라도 실패하면 이미 처리된 대상은 자동으로 복구합니다.

---

## 🎨 외관 및 로컬 데이터

macOS의 라이트/다크 모드를 따릅니다. **외관…**에서 투명도를 70%–100%로 실시간 조정할 수 있으며 기본값은 92%입니다.

설정 파일:

```text
~/Library/Application Support/旭影的摄影工具集/ui_config.json
```

이전 버전의 되돌리기 기록과 호환하기 위해 업무 백업 폴더는 이전 이름을 유지합니다. 자세한 내용은 [전체 안내의 로컬 데이터 절](docs/使用说明.md#8-本地数据与隐私)을 참고하세요.

---

<a id="build"></a>

## 🧰 소스에서 빌드

```bash
chmod +x build_app.sh
./build_app.sh
```

스크립트는 전체 테스트를 실행한 뒤 Apple Silicon과 Intel을 모두 지원하는 App, ZIP, DMG를 생성합니다.

기본 빌드는 ad-hoc 서명을 사용합니다. 첫 실행 경고 없이 배포하려면 Apple Developer ID Application 인증서와 `notarytool` 프로필을 설정하세요.

---

## 📦 이전 독립 스크립트

추적과 참고를 위해 최초의 세 독립 스크립트도 저장소에 남아 있습니다.

- `根据时间重命名文件排序.py`
- `根据RAW:JPG双向同步.py`
- `同步颜色与星号标记.py`

일상적으로는 `main.py` 또는 macOS 앱을 사용하세요. 통합 앱은 재귀 스캔 통계, 충돌 방지, 더 완전한 되돌리기를 제공합니다.

---

## 🤝 기여 및 피드백

- 변경을 보내기 전에 [CONTRIBUTING.md](CONTRIBUTING.md)를 읽어 주세요.
- 버그와 기능 제안은 [Issue](https://github.com/xuying-studio/xuying-photo-toolkit/issues)에 등록하세요.
- 덮어쓰기, 데이터 손실, 정보 노출 가능성이 있는 문제는 [SECURITY.md](SECURITY.md)에 따라 비공개로 보고하세요.

Issue에 실제 사진, 전체 개인 경로, 휴지통 기록, 개인정보가 포함된 EXIF/XMP를 업로드하지 마세요.

---

<a id="license"></a>

## 📄 라이선스

[MIT License](LICENSE) © 2026 旭影
