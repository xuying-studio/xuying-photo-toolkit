#!/usr/bin/env python3
"""
给同源选片标记 - 双向同步程序 (Adobe Bridge)

将 Adobe Bridge 标记的星标和/或颜色标签在 JPG 和 RAW 文件之间双向同步。
- 星标存储在 <xmp:Rating> 字段 (0-5)
- 颜色标签存储在 <xmp:Label> 字段 ("Select", "Approved" 等)
- RAW 文件通过 .xmp 侧车文件读写，安全不损坏原始 RAW

用法: python3 sync_star_ratings.py
"""

import os
import sys
import json
import re
import base64
from pathlib import Path
from datetime import datetime
from collections import Counter

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────

JPEG_EXTENSIONS = {".jpg", ".jpeg", ".JPG", ".JPEG"}

RAW_EXTENSIONS = {
    ".ARW",  # Sony
    ".CR2", ".CR3", ".CRW",  # Canon
    ".NEF", ".NRW",  # Nikon
    ".RAF",  # Fujifilm
    ".RW2",  # Panasonic
    ".ORF",  # Olympus
    ".PEF",  # Pentax
    ".DNG",  # Leica / Pentax / DJI / 通用
    ".X3F",  # Sigma
    ".3FR", ".FFF",  # Hasselblad
    ".SRW",  # Samsung
    ".MRW",  # Minolta
    ".MOS",  # Leaf
    ".ERF",  # Epson
    ".IIQ",  # Phase One
    ".KDC",  # Kodak
    ".MEF",  # Mamiya
    ".RAW",  # Panasonic（老款）/ 通用
}

BACKUP_DIR = os.path.expanduser("~/.sync_star_backups")
MAX_PREVIEW_ITEMS = 10

# ── 正则 ──
RE_RATING_ATTR = re.compile(rb'xmp:Rating\s*=\s*"([0-5])"')
RE_RATING_ELEM = re.compile(rb"<xmp:Rating>([0-5])</xmp:Rating>")
RE_LABEL_ATTR = re.compile(rb'xmp:Label\s*=\s*"([^"]*)"')
RE_LABEL_ELEM = re.compile(rb"<xmp:Label>([^<]*)</xmp:Label>")

LABEL_COLORS: dict[str, str] = {
    "Select":   "🔴 红色",
    "Second":   "🟡 黄色",
    "Approved": "🟢 绿色",
    "Review":   "🔵 蓝色",
    "To Do":    "🟣 紫色",
    "Red":      "🔴 红色",
    "Yellow":   "🟡 黄色",
    "Green":    "🟢 绿色",
    "Blue":     "🔵 蓝色",
    "Purple":   "🟣 紫色",
}

# 哨兵: 区分"不修改"和"删除"
_MISSING = object()


def _label_display(value: str | None) -> str:
    if value is None:
        return "无"
    if value == "":
        return "无"
    color = LABEL_COLORS.get(value, "")
    return f"{value}({color})" if color else value


# ──────────────────────────────────────────────
# XMP 读写 — 侧车优先，安全不损坏原始文件
# ──────────────────────────────────────────────

def _read_file_bytes(filepath: str) -> bytes | None:
    try:
        with open(filepath, "rb") as f:
            return f.read()
    except (OSError, PermissionError):
        return None


def _sidecar_path(filepath: str) -> str:
    """返回侧车文件路径。格式为 文件名.xmp（不含原扩展名）。
    例如: /path/DSC0001.ARW → /path/DSC0001.xmp
    """
    p = Path(filepath)
    return str(p.parent / (p.stem + ".xmp"))


def _sidecar_old_naming(filepath: str) -> str:
    """旧版命名的侧车路径: 完整文件名 + .xmp（如 DSC0001.ARW.xmp）。
    只用于兼容旧数据。"""
    return filepath + ".xmp"


def _read_sidecar_xml(filepath: str) -> str | None:
    # 由下面的 section 204 定义，此处占位
    pass


def _write_sidecar_new(path: str, xml: str) -> bool:
    """写入侧车文件（按给定路径）。"""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml)
        return True
    except (OSError, PermissionError):
        return False


def read_xmp_rating(content: bytes) -> int | None:
    m = RE_RATING_ATTR.search(content) or RE_RATING_ELEM.search(content)
    return int(m.group(1)) if m else None


def read_xmp_label(content: bytes) -> str | None:
    m = RE_LABEL_ATTR.search(content) or RE_LABEL_ELEM.search(content)
    return m.group(1).decode("utf-8", errors="replace") if m else None


def read_file_rating(filepath: str) -> int:
    """读取文件的星标（0-5）。
    RAW: 只从侧车读取（不 fallback 内嵌 XMP）。
    JPG: 只从内嵌 XMP 读取（JPG 不应有侧车，内嵌 XMP 是权威源）。
    """
    if _is_raw_ext(Path(filepath).suffix):
        # RAW: 只看侧车
        rating = _read_sidecar_prop(filepath, read_xmp_rating)
        return rating if rating is not None else 0
    # JPG: 只看内嵌 XMP
    content = _read_file_bytes(filepath)
    if content is None:
        return 0
    r = read_xmp_rating(content)
    return r if r is not None else 0


def read_file_label(filepath: str) -> str | None:
    """读取文件的颜色标签。
    RAW: 只从侧车读取。
    JPG: 只从内嵌 XMP 读取。
    """
    if _is_raw_ext(Path(filepath).suffix):
        # RAW: 只看侧车
        label = _read_sidecar_prop(filepath, read_xmp_label)
        return label
    # JPG: 只看内嵌 XMP
    content = _read_file_bytes(filepath)
    if content is None:
        return None
    return read_xmp_label(content)


def _read_sidecar_prop(filepath, reader):
    """从侧车中读取属性。新命名优先，兼容旧命名。"""
    # 新命名优先
    sidecar = _sidecar_path(filepath)
    if os.path.exists(sidecar):
        content = _read_file_bytes(sidecar)
        if content is not None:
            return reader(content)
    # 兼容旧命名
    old = _sidecar_old_naming(filepath)
    if os.path.exists(old):
        content = _read_file_bytes(old)
        if content is not None:
            return reader(content)
    return None


# ── .xmp 侧车读取 / 创建 ──

def _read_sidecar_xml(filepath: str) -> str | None:
    """读取已有 .xmp 侧车的 XML 文本。先试新命名，兼容旧 .ARW.xmp 命名。
    如果只找到旧命名文件，自动迁移到新命名后删除旧文件。"""
    # 新命名优先
    sidecar = _sidecar_path(filepath)
    if os.path.exists(sidecar):
        content = _read_file_bytes(sidecar)
        if content:
            return content.decode("utf-8", errors="replace")

    # 兼容旧命名 — 如果存在 .ARW.xmp 则迁移到新命名
    old = _sidecar_old_naming(filepath)
    if os.path.exists(old):
        content = _read_file_bytes(old)
        if content:
            text = content.decode("utf-8", errors="replace")
            _write_sidecar_new(sidecar, text)
            os.remove(old)
            return text
    return None


def _create_sidecar_xml(rating: int | None, label: str | None) -> str:
    """生成标准 .xmp 侧车 XML。"""
    rating_elem = f"\n   <xmp:Rating>{rating}</xmp:Rating>" if rating is not None else ""
    label_elem = f"\n   <xmp:Label>{label}</xmp:Label>" if label is not None else ""
    return f"""<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0-c000">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:xmp="http://ns.adobe.com/xap/1.0/">{rating_elem}{label_elem}
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""


def _write_sidecar(filepath: str, xml: str) -> bool:
    """写入侧车文件。使用新命名格式（filename.xmp）。"""
    return _write_sidecar_new(_sidecar_path(filepath), xml)


def _delete_sidecar(filepath: str) -> bool:
    """删除侧车文件。同时尝试清理新旧两种命名。"""
    deleted = False
    for getter in (_sidecar_path, _sidecar_old_naming):
        path = getter(filepath)
        if os.path.exists(path):
            try:
                os.remove(path)
                deleted = True
            except (OSError, PermissionError):
                pass
    return deleted


# ── 侧车内容更新 ──

def _update_sidecar_xml(xml: str, rating: int | None, label: str | object) -> tuple[str, bool]:
    """在侧车 XML 中更新 Rating/Label。返回 (新XML, 是否修改)。"""
    changed = False

    if rating is not None:
        new_val = str(rating)
        m = RE_RATING_ATTR.search(xml.encode()) or RE_RATING_ELEM.search(xml.encode())
        if m:
            if m.group(1).decode() != new_val:
                xml = xml[:m.start(1)] + new_val + xml[m.end(1):]
                changed = True
        else:
            # 在 xmp description 块中插入
            xml, c = _insert_xml_prop_into_text(xml, "Rating", new_val)
            changed = changed or c

    if label is not _MISSING:
        new_label = "" if label is None else label
        m = RE_LABEL_ATTR.search(xml.encode()) or RE_LABEL_ELEM.search(xml.encode())
        if m:
            if m.group(1).decode() != new_label:
                xml = xml[:m.start(1)] + new_label + xml[m.end(1):]
                changed = True
        elif new_label != "":
            xml, c = _insert_xml_prop_into_text(xml, "Label", new_label)
            changed = changed or c

    return xml, changed


def _insert_xml_prop_into_text(xml: str, prop_name: str, value: str) -> tuple[str, bool]:
    """在侧车 XML 的 xmp Description 块中插入属性。"""
    elem = f"\n   <xmp:{prop_name}>{value}</xmp:{prop_name}>"

    # 找到 xmlns:xmp 所在的 Description 块
    m = re.search(r'(<rdf:Description[^>]*xmlns:xmp=[^>]*>)', xml)
    if m:
        ins = m.end()
        return xml[:ins] + elem + xml[ins:], True

    # Fallback: 在 </rdf:Description> 之前
    idx = xml.find("</rdf:Description>")
    if idx >= 0:
        return xml[:idx] + elem + "\n " + xml[idx:], True

    return xml, False


# ── 写入目标文件 ──

def write_props_to_target(target_path: str, is_raw: bool,
                          rating: int | None = None,
                          label: str | object = _MISSING) -> bool:
    """
    将星标和/或标签写入目标文件。
    rating=None 表示不修改星标，label=_MISSING 表示不修改标签。
    对 RAW: 始终通过 .xmp 侧车写入，永不修改原始 RAW 文件。
    对 JPG: 直接修改内嵌 XMP（JPG 无 TIFF 偏移问题）。
    """
    if is_raw:
        # RAW: 始终通过 .xmp 侧车写入，永不修改原始 RAW 文件
        sidecar_xml = _read_sidecar_xml(target_path)

        if sidecar_xml is not None:
            # 已有侧车 — 更新
            new_xml, changed = _update_sidecar_xml(sidecar_xml, rating, label)
            if not changed:
                return True
            return _write_sidecar(target_path, new_xml)
        else:
            # 无侧车 — 创建新侧车
            actual_rating = rating
            actual_label = None if label is _MISSING else ("" if label is None else label)

            # 检查是否需要创建侧车
            # 注意：不参考 RAW 内嵌 XMP，因为侧车才是权威来源
            need_sidecar = False
            if actual_rating is not None and actual_rating > 0:
                need_sidecar = True
            if actual_label is not None and actual_label != "":
                need_sidecar = True

            if not need_sidecar:
                return True

            new_xml = _create_sidecar_xml(
                actual_rating if actual_rating is not None and actual_rating > 0 else 0,
                actual_label if actual_label else None)
            return _write_sidecar(target_path, new_xml)
    else:
        # JPG: 直接修改内嵌 XMP（安全）
        ok = True
        if rating is not None:
            ok = _write_xmp_prop_to_file(target_path, b"xmp:Rating", str(rating),
                                          RE_RATING_ATTR, RE_RATING_ELEM) and ok
        if label is not _MISSING:
            lbl = "" if label is None else label
            ok = _write_xmp_prop_to_file(target_path, b"xmp:Label", lbl,
                                          RE_LABEL_ATTR, RE_LABEL_ELEM) and ok
        return ok


# ── JPG 内嵌 XMP 安全写入（仅用于 JPG） ──

def _write_xmp_prop_to_file(filepath: str, prop_name: bytes,
                              new_val: str | None,
                              attr_re: re.Pattern,
                              elem_re: re.Pattern) -> bool:
    content = _read_file_bytes(filepath)
    if content is None:
        return False

    new_content, changed = _replace_xmp_prop(content, prop_name, new_val,
                                              attr_re, elem_re)
    if not changed:
        return True

    try:
        backup = content
        with open(filepath, "wb") as f:
            f.write(new_content)
        return True
    except (OSError, PermissionError):
        try:
            with open(filepath, "wb") as f:
                f.write(backup)
        except Exception:
            pass
        return False


def _replace_xmp_prop(content: bytes, prop_name: bytes,
                       new_val: str | None,
                       attr_re: re.Pattern,
                       elem_re: re.Pattern) -> tuple[bytes, bool]:
    if new_val is None:
        # 删除字段 — 只匹配元素形式（更加安全）
        m = elem_re.search(content)
        if m is None:
            return content, False
        return content[:m.start()] + content[m.end():], True

    new_bytes = new_val.encode()

    for re_pat in (attr_re, elem_re):
        m = re_pat.search(content)
        if m:
            if m.group(1) == new_bytes:
                return content, False
            return content[:m.start(1)] + new_bytes + content[m.end(1):], True

    if prop_name == b"xmp:Rating":
        elem = f"\n  <xmp:Rating>{new_val}</xmp:Rating>".encode()
    else:
        elem = f"\n  <xmp:Label>{new_val}</xmp:Label>".encode()

    for ns in (b"xmlns:xmp='http://ns.adobe.com/xap/1.0/'",
               b'xmlns:xmp="http://ns.adobe.com/xap/1.0/"'):
        idx = content.find(ns)
        if idx >= 0:
            tag_close = content.find(b">", idx)
            if tag_close >= 0:
                return content[:tag_close + 1] + elem + content[tag_close + 1:], True

    desc_end = content.find(b"</rdf:Description>")
    if desc_end >= 0:
        elem2 = elem + b"\n "
        return content[:desc_end] + elem2 + content[desc_end:], True

    return content, False


# ──────────────────────────────────────────────
# 扫描与匹配
# ──────────────────────────────────────────────

def _find_matching(source_path: str, target_exts: set[str]) -> str | None:
    p = Path(source_path)
    base = p.stem
    parent = p.parent
    for ext in target_exts:
        for variant in (ext, ext.upper(), ext.lower()):
            candidate = parent / f"{base}{variant}"
            if candidate.exists():
                return str(candidate)
    return None


def _is_raw_ext(ext: str) -> bool:
    return ext.upper() in {e.upper() for e in RAW_EXTENSIONS}


def scan_directory(dir_path: str) -> dict:
    jpg_marked = []
    raw_marked = []

    # 匹配 .xmp 文件 — 排除旧命名格式
    all_files = [f for f in Path(dir_path).iterdir()
                 if f.is_file() and not f.name.startswith(".")
                 and f.suffix.lower() != ".xmp"]

    total = len(all_files)
    for idx, f in enumerate(all_files):
        _progress_bar(idx + 1, total, "扫描中")

        content = _read_file_bytes(str(f))
        if content is None:
            continue

        # 只对 RAW 文件检查侧车；JPG 以内嵌 XMP 为准
        rating = read_xmp_rating(content)
        label = read_xmp_label(content)

        if _is_raw_ext(f.suffix):
            sidecar = _sidecar_path(str(f))
            old_sidecar = _sidecar_old_naming(str(f))
            if os.path.exists(sidecar):
                sidecar_content = _read_file_bytes(sidecar)
            elif os.path.exists(old_sidecar):
                sidecar_content = _read_file_bytes(old_sidecar)
            else:
                sidecar_content = None

            if sidecar_content:
                sr = read_xmp_rating(sidecar_content)
                sl = read_xmp_label(sidecar_content)
                if sr is not None:
                    rating = sr
                if sl is not None:
                    label = sl

        has_rating = rating is not None and rating > 0
        has_label = label is not None and label != ""
        if not has_rating and not has_label:
            continue

        ext = f.suffix
        entry = {
            "path": str(f),
            "name": f.name,
            "rating": rating if rating is not None else 0,
            "label": label,
        }

        if ext in JPEG_EXTENSIONS:
            entry["target"] = _find_matching(str(f), RAW_EXTENSIONS)
            entry["target_name"] = Path(entry["target"]).name if entry["target"] else None
            jpg_marked.append(entry)
        elif _is_raw_ext(ext):
            entry["target"] = _find_matching(str(f), JPEG_EXTENSIONS)
            entry["target_name"] = Path(entry["target"]).name if entry["target"] else None
            raw_marked.append(entry)

    return {"jpg_marked": jpg_marked, "raw_marked": raw_marked}


# ──────────────────────────────────────────────
# 显示工具
# ──────────────────────────────────────────────

def _progress_bar(current: int, total: int, label: str = "", width: int = 36):
    if total <= 0:
        return
    ratio = current / total
    filled = int(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    print(f"\r  {label} [{bar}] {current}/{total}", end="", flush=True)
    if current >= total:
        print()


def _print_sync_preview(pairs: list[dict]):
    for i, r in enumerate(pairs):
        if i >= MAX_PREVIEW_ITEMS:
            print(f"    ... 还有 {len(pairs) - MAX_PREVIEW_ITEMS} 个文件未显示")
            break
        current_r = read_file_rating(r["target"])
        current_l = read_file_label(r["target"])
        target_r = r.get("sync_rating")
        target_l = r.get("sync_label")

        parts = [f"{r['target_name']}:"]
        if target_r is not None:
            parts.append(f"{current_r}★→{target_r}★")
        if target_l is not None:
            cl = _label_display(current_l)
            tl = _label_display(target_l)
            parts.append(f"标签 [{cl}]→[{tl}]")
        print(f"    {'  '.join(parts)}")


# ──────────────────────────────────────────────
# 备份与撤回
# ──────────────────────────────────────────────

def backup_targets(pairs: list[dict], is_raw_target: bool) -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)

    entries = {}
    total = len(pairs)
    for idx, r in enumerate(pairs):
        _progress_bar(idx + 1, total, "备份中")
        tgt = r["target"]
        has_sidecar = (os.path.exists(_sidecar_path(tgt))
                       or os.path.exists(_sidecar_old_naming(tgt)))

        entry = {
            "path": tgt,
            "is_raw": is_raw_target,
            "original_rating": read_file_rating(tgt),
            "original_label": read_file_label(tgt),
            "has_sidecar": has_sidecar,
        }

        if has_sidecar:
            # 新命名优先，兼容旧命名
            sc_content = (_read_file_bytes(_sidecar_path(tgt))
                          or _read_file_bytes(_sidecar_old_naming(tgt)))
            if sc_content:
                entry["sidecar_content_base64"] = base64.b64encode(sc_content).decode("ascii")

        entries[tgt] = entry

    backup_path = os.path.join(
        BACKUP_DIR,
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
        f"{re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(pairs[0]['path']).stem)}.json")

    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "direction": "RAW" if is_raw_target else "JPG",
            "entries": entries,
        }, f, ensure_ascii=False, indent=2)

    return backup_path


def undo_sync(backup_path: str | None = None):
    if backup_path:
        if not os.path.exists(backup_path):
            print(f"\n📭 备份文件不存在: {backup_path}\n")
            return
        _do_undo(backup_path)
        return

    if not os.path.isdir(BACKUP_DIR):
        print("\n📭 没有找到任何备份文件。\n")
        return

    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")], reverse=True)
    if not backups:
        print("\n📭 没有找到任何备份文件。\n")
        return

    if len(backups) == 1:
        _do_undo(os.path.join(BACKUP_DIR, backups[0]))
    else:
        print("\n📂 找到多个备份文件：")
        for i, b in enumerate(backups):
            bp = os.path.join(BACKUP_DIR, b)
            try:
                with open(bp, "r") as f:
                    data = json.load(f)
                print(f"  [{i + 1}] {b}  ({data.get('timestamp','?')}, "
                      f"{data.get('direction','?')}: {len(data.get('entries',{}))} 个)")
            except Exception:
                print(f"  [{i + 1}] {b}")
        print()
        choice = input(f"请输入编号 (1-{len(backups)}), 或按 Enter 取消: ").strip()
        if not choice:
            print("已取消。"); return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(backups):
                _do_undo(os.path.join(BACKUP_DIR, backups[idx]))
            else:
                print("编号无效。")
        except ValueError:
            print("输入无效。")


def _do_undo(backup_path: str):
    with open(backup_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", {})
    if not entries:
        print("\n📭 备份文件为空。\n")
        return

    print(f"\n{'─' * 50}")
    print(f"  ↩ 撤回操作")
    print(f"  时间: {data.get('timestamp', '?')}  |  方向: {data.get('direction', '?')}")
    print(f"  文件数: {len(entries)}")
    print(f"{'─' * 50}")

    succeeded, unchanged, failed = 0, 0, 0
    total = len(entries)
    idx = 0
    for tgt_path, entry in entries.items():
        idx += 1
        _progress_bar(idx, total, "撤回中")

        if not os.path.exists(tgt_path):
            failed += 1; continue

        target_r = entry["original_rating"]
        target_l = entry.get("original_label")
        current_r = read_file_rating(tgt_path)
        current_l = read_file_label(tgt_path)

        if current_r == target_r and current_l == target_l:
            unchanged += 1; continue

        sidecar = _sidecar_path(tgt_path)
        is_raw = entry.get("is_raw", False)

        # 有侧车备份 -> 直接恢复侧车
        if entry.get("has_sidecar") and "sidecar_content_base64" in entry:
            try:
                with open(sidecar, "wb") as f:
                    f.write(base64.b64decode(entry["sidecar_content_base64"]))
                succeeded += 1
            except Exception:
                failed += 1
        # 无侧车且目标是全部清空的 -> 删除创建的侧车
        elif target_r == 0 and target_l is None and not entry.get("has_sidecar"):
            _delete_sidecar(tgt_path)
            succeeded += 1
        else:
            undo_label = "" if target_l is None else target_l
            if write_props_to_target(tgt_path, is_raw, target_r, undo_label):
                succeeded += 1
            else:
                failed += 1

    print(f"\n{'─' * 50}")
    print(f"撤回完成: {succeeded} 个成功, {unchanged} 个无需修改" +
          (f", {failed} 个失败" if failed else ""))

    if failed == 0:
        os.remove(backup_path)
        print("备份文件已清理。")
    else:
        print(f"备份文件保留: {backup_path}")


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────

def main():
    print("=" * 56)
    print("  🎯 给同源选片标记 — RAW ↔ JPG 双向同步")
    print("  Adobe Bridge XMP: 星标 ★ + 颜色标签 🔴🟡🟢🔵🟣")
    print("=" * 56)

    while True:
        print()
        dir_path = input("📁 请输入照片所在的文件夹路径: ").strip()
        if not dir_path:
            print("⛔ 路径不能为空。"); continue
        dir_path = os.path.expanduser(dir_path)
        if not os.path.isdir(dir_path):
            print(f"⛔ 路径不存在: {dir_path}"); continue
        break

    print(f"\n🔍 正在扫描: {dir_path}")
    data = scan_directory(dir_path)

    jpg_marked = data["jpg_marked"]
    raw_marked = data["raw_marked"]

    if not jpg_marked and not raw_marked:
        print("\n📭 未找到任何带 Bridge 星标或颜色标签的文件。")
        return

    _print_stats(jpg_marked, raw_marked)

    jpg_with_match = [r for r in jpg_marked if r["target"]]
    raw_with_match = [r for r in raw_marked if r["target"]]

    print(f"\n{'─' * 50}")
    print(f"  请选择要同步的内容:")
    print(f"{'─' * 50}")
    print(f"  [1] 仅同步星标 (★)")
    print(f"  [2] 仅同步颜色标签")
    print(f"  [3] 同步星标和颜色标签（推荐）")
    print()
    attr_choice = input("请输入选项 (1/2/3): ").strip()
    if attr_choice == "1":
        sync_rating, sync_label = True, False
    elif attr_choice == "2":
        sync_rating, sync_label = False, True
    elif attr_choice == "3":
        sync_rating, sync_label = True, True
    else:
        print("输入无效，已取消。"); return

    jpg_candidates = []
    for r in jpg_with_match:
        if (sync_rating and r["rating"] > 0) or \
           (sync_label and r["label"] is not None and r["label"] != ""):
            jpg_candidates.append(r)

    raw_candidates = []
    for r in raw_with_match:
        if (sync_rating and r["rating"] > 0) or \
           (sync_label and r["label"] is not None and r["label"] != ""):
            raw_candidates.append(r)

    options = []
    if jpg_candidates:
        options.append(("1", "JPG → RAW", jpg_candidates, True))
    if raw_candidates:
        options.append(("2", "RAW → JPG", raw_candidates, False))

    if not options:
        print("\n📭 没有可同步的匹配文件。")
        return

    if len(options) == 1:
        _, direction, pairs, is_raw_target = options[0]
        print(f"\n💡 仅有「{direction}」方向可同步。")
    else:
        print(f"\n{'─' * 50}")
        print(f"  请选择同步方向:")
        print(f"{'─' * 50}")
        for num, direction, pairs, _ in options:
            d = "星标 + 标签" if (sync_rating and sync_label) else ("星标" if sync_rating else "标签")
            label = f"  [{num}] {direction} — 将 {d} 从 JPG 同步到 RAW" if num == "1" else \
                    f"  [{num}] {direction} — 将 {d} 从 RAW 同步到 JPG"
            print(label)
        print()
        choice = input("请输入选项 (1 或 2): ").strip()
        if choice == "1":
            _, direction, pairs, is_raw_target = options[0]
        elif choice == "2":
            _, direction, pairs, is_raw_target = options[1]
        else:
            print("输入无效，已取消。"); return

    for r in pairs:
        r["sync_rating"] = r["rating"] if sync_rating else None
        r["sync_label"] = r["label"] if sync_label else None

    print(f"\n{'─' * 50}")
    print(f"  将要同步: {direction}")
    if sync_rating and sync_label:
        print(f"  内容: 星标 + 颜色标签")
    elif sync_rating:
        print(f"  内容: 星标")
    else:
        print(f"  内容: 颜色标签")
    print(f"{'─' * 50}")
    _print_sync_preview(pairs)

    print()
    choice = input(f"是否执行同步？(y/n): ").strip().lower()
    if choice not in ("y", "yes"):
        print("已取消。"); return

    backup_path = backup_targets(pairs, is_raw_target)
    print(f"\n💾 备份已保存: {backup_path}")

    print(f"\n{'─' * 50}")
    print(f"  ⚡ 正在同步 ({direction})...")
    print(f"{'─' * 50}")

    succeeded, unchanged, failed = 0, 0, 0
    total = len(pairs)
    for idx, r in enumerate(pairs):
        _progress_bar(idx + 1, total, "同步中")

        target_r = r.get("sync_rating")
        target_l = r.get("sync_label")
        current_r = read_file_rating(r["target"])
        current_l = read_file_label(r["target"])

        r_changed = (target_r is not None and current_r != target_r)
        l_changed = (target_l is not None and current_l != target_l)

        if not r_changed and not l_changed:
            unchanged += 1; continue

        if write_props_to_target(r["target"], is_raw_target, target_r, target_l):
            succeeded += 1
        else:
            failed += 1

    print(f"\n{'─' * 50}")
    print(f"同步完成: {succeeded} 个成功, {unchanged} 个已是最新" +
          (f", {failed} 个失败" if failed else ""))

    if succeeded > 0:
        print()
        print("💡 需要撤回吗？")
        undo_choice = input("是否撤回本次同步？(y/n): ").strip().lower()
        if undo_choice in ("y", "yes"):
            undo_sync(backup_path)
        else:
            print(f"\n💡 备份已保存: {backup_path}")
            print(f"   撤回命令: python3 sync_star_ratings.py --undo")

    print("\n✨ 完毕！")


def _print_stats(jpg_marked, raw_marked):
    print(f"\n{'─' * 50}")
    print(f"  📊 扫描结果")
    print(f"{'─' * 50}")

    for name, items, match_label in [
        ("JPG", jpg_marked, "RAW"),
        ("RAW", raw_marked, "JPG"),
    ]:
        if not items:
            continue
        print(f"  带标记的 {name} 文件: {len(items)} 个")

        for stars in range(5, 0, -1):
            count = sum(1 for r in items if r["rating"] == stars)
            if count > 0:
                print(f"        {'★' * stars}{'☆' * (5 - stars)}  {count} 个")

        labels = [r["label"] for r in items if r["label"] is not None and r["label"] != ""]
        if labels:
            lc = Counter(labels)
            for lbl, cnt in lc.most_common():
                color = LABEL_COLORS.get(lbl, lbl)
                print(f"        🏷 {lbl}({color})  {cnt} 个")

        matched = [r for r in items if r["target"]]
        unmatched = [r for r in items if not r["target"]]
        print(f"      匹配到 {match_label}:    {len(matched)} 个")
        if unmatched:
            print(f"      未匹配 {match_label}:    {len(unmatched)} 个")


def cli():
    if len(sys.argv) > 1 and sys.argv[1] in ("--undo", "-u"):
        print("=" * 56)
        print("  ↩  撤回同步")
        print("=" * 56)
        undo_sync(sys.argv[2] if len(sys.argv) > 2 else None)
    elif len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        print("选项:  --undo, -u 撤回  |  --help, -h 帮助")
    else:
        main()


if __name__ == "__main__":
    cli()
