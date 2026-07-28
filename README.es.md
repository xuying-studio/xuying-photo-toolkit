<div align="center">
  <h1>📷 Kit de Herramientas Fotográficas Xuying</h1>
  <p>Añade capacidades de organizar, emparejar y sincronizar a tu flujo fotográfico.</p>
  <p>Renombra por fecha de captura, limpia archivos RAW/JPG sin pareja y sincroniza estrellas y etiquetas de color de Adobe Bridge desde una aplicación macOS.</p>
  <p>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/xuying-studio/xuying-photo-toolkit?style=flat-square" alt="MIT License"></a>
    <img src="https://img.shields.io/badge/macOS-11%2B-000000?style=flat-square&amp;logo=apple" alt="macOS 11+">
    <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.10+">
  </p>
  <p><img src="assets/app_icon.png" width="144" alt="Icono de Kit de Herramientas Fotográficas Xuying"></p>
  <p>
    <a href="#quick-start">Inicio rápido</a> ·
    <a href="#features">Funciones</a> ·
    <a href="#safety">Seguridad</a> ·
    <a href="docs/使用说明.md">Guía completa</a> ·
    <a href="#build">Compilar</a> ·
    <a href="CONTRIBUTING.md">Contribuir</a> ·
    <a href="#license">Licencia</a>
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

## ¿Por qué lo necesitas?

Después de una sesión, estas tareas repetitivas son fáciles de hacer mal si se realizan a mano:

- 📁 Los RAW, JPG y sidecars XMP están repartidos en subcarpetas y necesitan un esquema de nombres basado en la fecha de captura.
- 🧹 Las exportaciones o copias dejan JPG o RAW sin pareja, pero borrarlos en lote parece arriesgado.
- ⭐ Las selecciones hechas en Adobe Bridge deben copiarse entre JPG y RAW.
- 🛡️ El procesamiento por lotes solo es útil si evita sobrescrituras, borrados accidentales y cambios imposibles de revertir.

Xuying Photo Toolkit convierte el flujo en: **escanear y previsualizar → revisar las cantidades → confirmar y ejecutar → deshacer cuando sea necesario**.

---

<a id="features"></a>

## ✨ ¿Qué hace?

| Función | Cuándo usarla | Protección de archivos |
| --- | --- | --- |
| 🕒 Renombrar por fecha de captura | Para unificar nombres de RAW, JPG y sidecars XMP | Previsualización, bloqueo de conflictos, renombrado en dos fases y deshacer |
| 🧹 Limpieza de parejas RAW / JPG | Para encontrar archivos sin pareja con el mismo nombre | Mueve a la Papelera de macOS y crea una copia de recuperación |
| ⭐ Sincronizar estrellas y colores | Para copiar marcas de Adobe Bridge entre RAW/JPG coincidentes | Los RAW solo reciben `.xmp`; los destinos se respaldan y pueden revertirse |

Todas las páginas escanean recursivamente la carpeta seleccionada y muestran el total, el estado de las parejas y la cantidad pendiente antes de ejecutar.
Durante el escaneo, la ejecución y el deshacer se muestran en tiempo real la cantidad actual, el total y el porcentaje completado.

> No necesitas memorizar comandos y ninguna foto se modifica antes de confirmar una operación.

---

<a id="safety"></a>

## ✅ Antes de empezar

| Aspecto | Comportamiento |
| --- | --- |
| 🔒 Privacidad | Las fotos, rutas y metadatos se procesan solo en tu Mac. La aplicación no sube ni sincroniza fotos. |
| 👀 Previsualización | Los tres flujos muestran una lista y estadísticas antes de cambiar archivos. |
| 🛡️ Sin sobrescrituras | Si existe el destino o hay un conflicto de nombres, la operación se detiene. |
| 🗑️ Sin borrado permanente | La limpieza mueve los archivos a la Papelera de macOS y conserva una copia local de seguridad. |
| ↩️ Deshacer | El renombrado, la recuperación de limpieza y la sincronización XMP conservan la última vía de recuperación. |
| 📷 RAW protegido | Nunca se escribe directamente en el RAW; los metadatos usan un sidecar `.xmp`. |

> ⚠️ Es una herramienta de procesamiento por lotes, no un sistema de copias de seguridad. Pruébala primero con una copia pequeña del proyecto.

---

<a id="quick-start"></a>

## 🚀 Inicio rápido

### Usar la aplicación macOS

1. Descarga el `.dmg` desde la página de [Releases](https://github.com/xuying-studio/xuying-photo-toolkit/releases).
2. Ábrelo y arrastra `旭影的摄影工具集.app` a Aplicaciones.
3. Abre la aplicación, selecciona una carpeta de fotos y pulsa primero **Escanear y previsualizar**.

> La versión actual usa una firma ad-hoc local y no está notarizada con Apple Developer ID. En otro Mac, el primer inicio puede requerir hacer clic derecho en la aplicación y elegir **Abrir**.

### Ejecutar desde el código fuente

Requisitos: macOS 11 o posterior, Python 3.10 o posterior y Tkinter proporcionado por macOS/Python.

```bash
git clone https://github.com/xuying-studio/xuying-photo-toolkit.git
cd xuying-photo-toolkit
python3 -m pip install -r requirements.txt
python3 main.py
```

### Primera ejecución segura

1. Copia un pequeño conjunto RAW/JPG a una carpeta de prueba.
2. Selecciona una función y pulsa **Escanear y previsualizar**.
3. Revisa las estadísticas y la lista pendiente.
4. Ejecuta y comprueba el resultado.
5. Procesa el proyecto completo solo después de validar la muestra.

Consulta la [guía completa](docs/使用说明.md) para formatos compatibles, reglas de nombres, recuperación y solución de problemas.

---

<a id="workflows"></a>

## 🧭 Cómo funcionan las tres herramientas

### 🕒 Renombrar por fecha de captura

La aplicación prefiere la fecha de captura EXIF y usa la fecha de modificación como alternativa:

```text
DSC26-07-25-00001.arw
DSC26-07-25-00001.jpg
DSC26-07-25-00001.xmp
```

Los sidecars del RAW coincidente se renombran junto con él. Los archivos que ya tienen este formato no cambian y la numeración continúa después del número máximo de ese día.

### 🧹 Limpieza de parejas RAW / JPG

La pareja se determina en la **misma carpeta**, usando el mismo nombre base y sin distinguir mayúsculas:

```text
A001.JPG  ↔  a001.ARW
```

Puedes elegir **JPG sin RAW** o **RAW sin JPG**. Los archivos van a la Papelera de macOS en lugar de borrarse permanentemente. La recuperación usa primero la copia de seguridad oculta y, si es necesario, Finder.

### ⭐ Sincronización de estrellas y etiquetas de Adobe Bridge

Se admiten las dos direcciones: `JPG → RAW` y `RAW → JPG`. Puedes sincronizar estrellas, etiquetas de color o ambas.

- Al escribir en RAW solo se crea o actualiza su sidecar `.xmp`.
- Al escribir en JPG se crea una copia completa antes de actualizar el XMP incrustado.
- Si falla un elemento de un lote, los destinos ya procesados se restauran automáticamente.

---

## 🎨 Apariencia y datos locales

La aplicación sigue la apariencia clara u oscura de macOS. El control **Apariencia…** permite ajustar en tiempo real la opacidad entre 70% y 100%; el valor predeterminado es 92%.

Configuración:

```text
~/Library/Application Support/旭影的摄影工具集/ui_config.json
```

Para mantener la compatibilidad con los registros de deshacer anteriores, las carpetas de respaldo conservan su nombre histórico. Consulta la [sección de datos locales](docs/使用说明.md#8-本地数据与隐私).

---

<a id="build"></a>

## 🧰 Compilar desde el código fuente

```bash
chmod +x build_app.sh
./build_app.sh
```

El script ejecuta toda la suite de pruebas y genera App, ZIP y DMG universales para Apple Silicon e Intel.

La compilación predeterminada usa firma ad-hoc. Para distribuir sin el aviso del primer inicio, configura un certificado Apple Developer ID Application y un perfil de `notarytool`.

---

## 📦 Scripts independientes históricos

El repositorio conserva los tres scripts originales como referencia:

- `根据时间重命名文件排序.py`
- `根据RAW:JPG双向同步.py`
- `同步颜色与星号标记.py`

Para el uso diario, se recomienda `main.py` o la aplicación macOS, que añade estadísticas recursivas, protección contra conflictos y una recuperación más completa.

---

## 🤝 Contribuciones y comentarios

- Lee [CONTRIBUTING.md](CONTRIBUTING.md) antes de enviar cambios.
- Abre un [Issue](https://github.com/xuying-studio/xuying-photo-toolkit/issues) para errores y solicitudes.
- Para posibles problemas de sobrescritura, pérdida de datos o divulgación, sigue [SECURITY.md](SECURITY.md) y repórtalos de forma privada.

No subas fotos reales, rutas personales completas, registros de la Papelera ni datos EXIF/XMP privados a un Issue.

---

<a id="license"></a>

## 📄 Licencia

[MIT License](LICENSE) © 2026 旭影
