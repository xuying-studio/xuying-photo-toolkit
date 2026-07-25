#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import json
import shutil
import re
from datetime import datetime
import exifread

SUPPORTED_EXT = {
    ".jpg", ".jpeg",
    ".arw", ".cr2", ".cr3",
    ".nef", ".raf", ".dng"
}
RAW_EXT = {".arw", ".cr2", ".cr3", ".nef", ".raf", ".dng"}
COUNTER_LEN = 5
BACKUP_FILE = os.path.expanduser("~/.photo_rename_backup.json")


def extract_original_number(filename):
    """
    从文件名中提取数字编号
    支持：DSC0001 / _DSC0123 / IMG_1234 / P0001234 等
    """
    match = re.search(r'(\d+)', filename)
    if match:
        return match.group(1)
    return None


def get_exif_time(path):
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
            dt = tags.get("EXIF DateTimeOriginal")
            if dt:
                return datetime.strptime(str(dt), "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None


def scan_files(folder):
    files = []
    raw_cnt = 0
    jpg_cnt = 0

    for root, _, filenames in os.walk(folder):
        for name in filenames:
            ext = os.path.splitext(name.lower())[1]
            if ext in SUPPORTED_EXT:
                full = os.path.join(root, name)
                files.append({
                    "path": full,
                    "name": name,
                    "ext": ext
                })
                if ext in RAW_EXT:
                    raw_cnt += 1
                else:
                    jpg_cnt += 1
    return files, raw_cnt, jpg_cnt


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📸 根据时间重命名文件排序")
        self.geometry("760x580")

        self.folder = ""
        self.files = []
        self.mapping = {}

        tk.Button(self, text="选择照片文件夹", command=self.select_folder).pack(pady=5)

        self.info_label = tk.Label(self, text="请选择文件夹", fg="gray")
        self.info_label.pack()

        tk.Button(self, text="预览重命名", command=self.preview).pack(pady=5)

        self.log = scrolledtext.ScrolledText(self, height=18)
        self.log.pack(fill=tk.BOTH, expand=True, padx=10)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="执行重命名", command=self.execute).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="撤回本次操作", command=self.undo).pack(side=tk.LEFT, padx=5)

    def log_text(self, text):
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)

    def select_folder(self):
        self.folder = filedialog.askdirectory()
        if not self.folder:
            return

        self.files, raw_cnt, jpg_cnt = scan_files(self.folder)
        total = raw_cnt + jpg_cnt

        self.info_label.config(
            text=f"📂 {self.folder}\n"
                 f"📸 共 {total} 个文件（RAW: {raw_cnt}, JPG: {jpg_cnt}）",
            fg="blue"
        )
        self.log.delete(1.0, tk.END)
        self.mapping.clear()

    def _generate_mapping(self):
        if not self.files:
            return False

        # 按“原始编号”分组
        groups = {}
        for f in self.files:
            num = extract_original_number(f["name"])
            if not num:
                continue
            groups.setdefault(num, []).append(f)

        # 按拍摄时间排序各组
        group_times = []
        for num, g in groups.items():
            dt = None
            for f in g:
                t = get_exif_time(f["path"]) or os.path.getmtime(f["path"])
                if isinstance(t, datetime):
                    dt = t
                else:
                    dt = datetime.fromtimestamp(t)
                break
            group_times.append((dt, num, g))

        group_times.sort()

        self.mapping.clear()
        last_date = None
        counter = 0

        for dt, num, g in group_times:
            date_str = dt.strftime("%y-%m-%d")
            if date_str != last_date:
                last_date = date_str
                counter = 1
            else:
                counter += 1

            for f in g:
                ext = f["ext"]
                new_name = f"DSC{date_str}-{counter:0{COUNTER_LEN}d}{ext}"
                new_path = os.path.join(os.path.dirname(f["path"]), new_name)
                self.mapping[f["path"]] = new_path

        return True

    def preview(self):
        self.log.delete(1.0, tk.END)
        if not self._generate_mapping():
            messagebox.showwarning("提示", "请先选择文件夹")
            return

        for old, new in self.mapping.items():
            self.log_text(f"{os.path.basename(old)}  →  {os.path.basename(new)}")

    def execute(self):
        if not self.mapping and not self._generate_mapping():
            messagebox.showwarning("提示", "请先选择文件夹")
            return

        backup = {}
        for old, new in self.mapping.items():
            if os.path.exists(new):
                self.log_text(f"⚠️ 跳过: {os.path.basename(new)}")
                continue
            shutil.move(old, new)
            backup[new] = old

        with open(BACKUP_FILE, "w") as f:
            json.dump(backup, f)

        self.log_text(f"✅ 完成，共处理 {len(backup)} 个文件")

    def undo(self):
        if not os.path.exists(BACKUP_FILE):
            messagebox.showinfo("提示", "无可撤回操作")
            return

        with open(BACKUP_FILE) as f:
            backup = json.load(f)

        for new, old in backup.items():
            if os.path.exists(new):
                shutil.move(new, old)

        os.remove(BACKUP_FILE)
        self.log_text("↩️ 已撤回")

if __name__ == "__main__":
    App().mainloop()
