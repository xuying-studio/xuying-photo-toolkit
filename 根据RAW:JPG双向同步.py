"""
本程序支持双向清理：
  JPG 模式 — 扫描 JPG，删除没有对应 RAW 文件的 JPG
  RAW 模式 — 扫描 RAW，删除没有对应 JPG 文件的 RAW

支持主流相机品牌的 RAW 格式（Sony/Canon/Nikon/Fujifilm/Olympus/Panasonic/Leica 等）
所有删除操作均使用 send2trash，文件进入回收站/废纸篓
删除后可按 1 键一键恢复本次删除的所有文件
"""

import os
import json
import tempfile
import platform
import subprocess
import send2trash

# ============================================================
# 主流相机品牌 RAW 格式扩展名（全部小写，用于不区分大小写比较）
# ============================================================
RAW_EXTENSIONS = {
    ".arw",   # Sony
    ".cr2",   # Canon
    ".cr3",   # Canon
    ".nef",   # Nikon
    ".nrw",   # Nikon（部分机型）
    ".raf",   # Fujifilm
    ".orf",   # Olympus / OM System
    ".rw2",   # Panasonic / Lumix
    ".pef",   # Pentax
    ".dng",   # Adobe 通用 DNG / Leica / Pentax / DJI / 部分手机
    ".3fr",   # Hasselblad
    ".fff",   # Hasselblad（部分机型）
    ".iiq",   # Phase One
    ".x3f",   # Sigma
    ".srw",   # Samsung
    ".gpr",   # GoPro
}

# 支持的 JPG 扩展名
JPG_EXTENSIONS = {".jpg", ".jpeg"}

# 撤销信息存储路径
UNDO_FILE = os.path.join(tempfile.gettempdir(), "photo_cleaner_undo.json")


def find_files_to_delete(folder_path, target_exts, pair_exts):
    """
    扫描 folder_path 下所有目标类型文件，
    返回「没有对应配对文件」的文件路径列表。

    - target_exts: 我们要检查的文件的扩展名集合（如 {".jpg", ".jpeg"}）
    - pair_exts:   配对文件的扩展名集合（如 raw_extensions）
    """
    to_delete = []

    for file_name in os.listdir(folder_path):
        file_lower = file_name.lower()
        ext = os.path.splitext(file_lower)[1]

        # 只处理 target 类型
        if ext not in target_exts:
            continue

        file_path = os.path.join(folder_path, file_name)
        base_name = os.path.splitext(file_path)[0]

        # 检查是否存在任意一种配对格式（扩展名不区分大小写）
        has_pair = False
        for pair_ext in pair_exts:
            if os.path.exists(base_name + pair_ext.lower()) or \
               os.path.exists(base_name + pair_ext.upper()):
                has_pair = True
                break

        if not has_pair:
            to_delete.append(file_path)

    return to_delete


def save_undo_info(deleted_files):
    """保存本次删除的文件路径，供撤销使用"""
    with open(UNDO_FILE, "w", encoding="utf-8") as f:
        json.dump(deleted_files, f, ensure_ascii=False, indent=2)


def load_undo_info():
    """读取上次删除的文件路径"""
    if os.path.exists(UNDO_FILE):
        with open(UNDO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def clear_undo_info():
    """清除撤销记录"""
    if os.path.exists(UNDO_FILE):
        os.remove(UNDO_FILE)


def restore_from_trash_macos(deleted_files):
    """
    macOS：通过 AppleScript 从废纸篓中找回文件，放回原始目录。
    返回成功恢复的文件数量。
    """
    restored = 0
    for original_path in deleted_files:
        filename = os.path.basename(original_path)
        original_dir = os.path.dirname(original_path)

        # 转义文件名中的特殊字符，防止 AppleScript 语法错误
        escaped_filename = filename.replace("\\", "\\\\").replace('"', '\\"')
        escaped_dir = original_dir.replace("\\", "\\\\").replace('"', '\\"')

        script = (
            f'tell application "Finder" to set trashItems to every item in trash\n'
            f'repeat with t in trashItems\n'
            f'    if name of t is "{escaped_filename}" then\n'
            f'        move t to POSIX file "{escaped_dir}"\n'
            f'        exit repeat\n'
            f'    end if\n'
            f'end repeat'
        )

        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                timeout=10,
            )
            print(f"  已恢复：{filename}")
            restored += 1
        except subprocess.CalledProcessError:
            print(f"  恢复失败：{filename}（文件可能已不在废纸篓中）")
        except subprocess.TimeoutExpired:
            print(f"  恢复超时：{filename}")

    return restored


def offer_undo():
    """检查是否有可撤销的操作，如有则提供一键恢复"""
    deleted_files = load_undo_info()
    if not deleted_files:
        return

    print()
    print("=" * 50)
    undo = input(
        f"输入 1 可一键恢复本次删除的 {len(deleted_files)} 个文件，按回车键退出："
    ).strip()

    if undo != "1":
        clear_undo_info()
        return

    # ---------- 执行恢复 ----------
    print()
    print("正在从废纸篓恢复文件...")

    current_os = platform.system()
    if current_os == "Darwin":
        restored = restore_from_trash_macos(deleted_files)
    else:
        print(
            f"当前系统（{current_os}）暂不支持一键恢复，请手动从回收站找回文件。"
        )
        print("需要恢复的文件：")
        for fp in deleted_files:
            print(f"  →  {os.path.basename(fp)}")
        clear_undo_info()
        return

    print()
    print(f"恢复完成！成功恢复 {restored}/{len(deleted_files)} 个文件。")
    clear_undo_info()


def main():
    print("=" * 50)
    print("  照片配对清理工具（RAW ↔ JPG）")
    print("=" * 50)
    print()

    # ---------- 选择文件夹 ----------
    folder_path = input("请输入要处理的文件夹路径：").strip()
    folder_path = os.path.expanduser(folder_path)  # 支持 ~ 路径

    if not os.path.isdir(folder_path):
        print(f"错误：路径 \"{folder_path}\" 不存在或不是文件夹。")
        input("按回车键退出...")
        return

    # ---------- 选择要删除的格式 ----------
    print()
    print("请问需要删除的格式是？")
    print("  [1] JPG（删除没有对应 RAW 的 JPG）")
    print("  [2] RAW（删除没有对应 JPG 的 RAW）")
    print()
    mode = input("请输入 1 或 2：").strip()

    if mode == "1":
        target_exts = JPG_EXTENSIONS
        pair_exts = RAW_EXTENSIONS
        target_label = "JPG"
        pair_label = "RAW"
    elif mode == "2":
        target_exts = RAW_EXTENSIONS
        pair_exts = JPG_EXTENSIONS
        target_label = "RAW"
        pair_label = "JPG"
    else:
        print(f"错误：无法识别 \"{mode}\"，请输入 1 或 2。")
        input("按回车键退出...")
        return

    # ---------- 扫描待删除文件 ----------
    print()
    print(f"正在扫描：{target_label} → 检查对应 {pair_label} 是否存在...")
    to_delete = find_files_to_delete(folder_path, target_exts, pair_exts)

    # ---------- 预览 ----------
    if not to_delete:
        print(f"没有需要清理的文件——所有 {target_label} 都有对应的 {pair_label}。")
        offer_undo()
        input("按回车键退出...")
        return

    print()
    print(f"将移动以下 {len(to_delete)} 个文件到回收站：")
    print("-" * 40)
    for fp in to_delete:
        print(f"  →  {os.path.basename(fp)}")
    print("-" * 40)

    confirm = input("确认执行？输入 1 确认，其他任意键取消：").strip()
    if confirm != "1":
        print("已取消，未修改任何文件。")
        offer_undo()
        input("按回车键退出...")
        return

    # ---------- 执行 ----------
    print()
    deleted = []
    for fp in to_delete:
        try:
            send2trash.send2trash(fp)
            print(f"已移动到回收站：{os.path.basename(fp)}")
            deleted.append(fp)
        except Exception as e:
            print(f"失败：{os.path.basename(fp)} — {e}")

    print()
    print(f"任务完成！共移动 {len(deleted)} 个文件到回收站。")

    # ---------- 保存撤销信息 ----------
    if deleted:
        save_undo_info(deleted)

    # ---------- 提供一键恢复 ----------
    offer_undo()

    input("按回车键退出...")


if __name__ == "__main__":
    main()
