import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox

class Notepad(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pythonメモ帳")
        self.geometry("900x650")

        # --- state ---
        self.filepath = None
        self.autosave_delay_ms = 2000  # 入力停止から2秒で保存（デバウンス）
        self._autosave_after_id = None
        self._last_save_ok = True
        self._last_save_ts = None

        # --- UI: top search bar ---
        top = tk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)

        tk.Label(top, text="検索:").pack(side="left")

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(top, textvariable=self.search_var, width=35)
        self.search_entry.pack(side="left", padx=(6, 6))

        tk.Button(top, text="前", command=self.find_prev, width=6).pack(side="left", padx=(0, 4))
        tk.Button(top, text="次", command=self.find_next, width=6).pack(side="left", padx=(0, 8))
        tk.Button(top, text="全ハイライト", command=self.highlight_all, width=10).pack(side="left", padx=(0, 4))
        tk.Button(top, text="クリア", command=self.clear_highlight, width=7).pack(side="left")

        # --- UI: text area + scrollbar ---
        mid = tk.Frame(self)
        mid.pack(fill="both", expand=True)

        self.text = tk.Text(mid, undo=True, wrap="word")
        yscroll = tk.Scrollbar(mid, command=self.text.yview)
        self.text.configure(yscrollcommand=yscroll.set)

        self.text.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        # --- UI: status bar ---
        self.status_var = tk.StringVar(value="準備完了")
        status = tk.Label(self, textvariable=self.status_var, anchor="w")
        status.pack(fill="x", padx=8, pady=(0, 6))

        # tags
        self.text.tag_config("match", background="yellow")

        # --- menu ---
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="新規", command=self.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="開く", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="名前を付けて保存", command=self.save_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.on_quit)
        menubar.add_cascade(label="ファイル", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="元に戻す", command=self.text.edit_undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="やり直す", command=self.text.edit_redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="検索へ", command=self.focus_search, accelerator="Ctrl+F")
        menubar.add_cascade(label="編集", menu=edit_menu)

        self.config(menu=menubar)

        # --- bindings ---
        self.bind("<Control-n>", lambda e: self.new_file())
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-Shift-S>", lambda e: self.save_as())
        self.bind("<Control-f>", lambda e: self.focus_search())

        # 検索: Enter=次, Shift+Enter=前
        self.search_entry.bind("<Return>", lambda e: self.find_next())
        self.search_entry.bind("<Shift-Return>", lambda e: self.find_prev())

        # 自動保存: テキスト変更検知
        self.text.bind("<<Modified>>", self._on_modified)

        # 起動時は一時ファイルに保存（=書きっぱなし）
        self._ensure_autosave_path()
        self._update_title()

        # 閉じるボタン
        self.protocol("WM_DELETE_WINDOW", self.on_quit)

    # ---------- file ops ----------
    def new_file(self):
        if not self._confirm_discard_if_needed():
            return
        self.text.delete("1.0", "end")
        self.filepath = None
        self._ensure_autosave_path()
        self._set_status("新規作成しました（自動保存は autosave.txt）")
        self._update_title()

    def open_file(self):
        if not self._confirm_discard_if_needed():
            return
        path = filedialog.askopenfilename(
            filetypes=[("テキスト", "*.txt"), ("すべて", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content)
            self.text.edit_modified(False)
            self.filepath = path
            self._set_status(f"開きました: {path}")
            self._update_title()
        except Exception as e:
            messagebox.showerror("エラー", f"開けませんでした:\n{e}")

    def save_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("テキスト", "*.txt"), ("すべて", "*.*")]
        )
        if not path:
            return
        self.filepath = path
        # すぐ保存（以降は自動上書き）
        self._autosave(force=True)
        self._set_status(f"保存先を設定しました: {path}")
        self._update_title()

    def on_quit(self):
        # 終了時は最後に保存を試みる（失敗しても終了はできる）
        self._autosave(force=True)
        if self.text.edit_modified():
            if not messagebox.askyesno("確認", "未保存の変更がある可能性があります。終了しますか？"):
                return
        self.destroy()

    def _confirm_discard_if_needed(self) -> bool:
        if self.text.edit_modified():
            return messagebox.askyesno("確認", "未保存の変更があります。破棄して進みますか？")
        return True

    # ---------- autosave ----------
    def _ensure_autosave_path(self):
        # 開いてない時のデフォルト自動保存先
        self.autosave_path = os.path.join(os.getcwd(), "autosave.txt")

    def _on_modified(self, event=None):
        # Modifiedフラグをクリアしないとイベントが連発しない/挙動が乱れる
        if self.text.edit_modified():
            self.text.edit_modified(False)

        # デバウンス：既存予約キャンセル→再予約
        if self._autosave_after_id is not None:
            self.after_cancel(self._autosave_after_id)
        self._autosave_after_id = self.after(self.autosave_delay_ms, self._autosave)

        self._update_title(dirty=True)

    def _autosave(self, force: bool = False):
        self._autosave_after_id = None

        path = self.filepath or self.autosave_path

        content = self.text.get("1.0", "end-1c")
        try:
            # 破損対策：一時ファイル→置換
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, path)

            self._last_save_ok = True
            self._last_save_ts = time.strftime("%H:%M:%S")
            self._set_status(f"自動保存しました: {os.path.basename(path)}（{self._last_save_ts}）")
            self._update_title(dirty=False)
        except Exception as e:
            self._last_save_ok = False
            self._set_status(f"保存失敗: {e}")

    # ---------- search ----------
    def focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")

    def clear_highlight(self):
        self.text.tag_remove("match", "1.0", "end")
        self._set_status("ハイライトをクリアしました")

    def highlight_all(self):
        needle = self.search_var.get()
        self.text.tag_remove("match", "1.0", "end")
        if not needle:
            self._set_status("検索語が空です")
            return

        count = 0
        idx = "1.0"
        while True:
            idx = self.text.search(needle, idx, stopindex="end", nocase=0)
            if not idx:
                break
            end = f"{idx}+{len(needle)}c"
            self.text.tag_add("match", idx, end)
            idx = end
            count += 1

        if count == 0:
            self._set_status("見つかりませんでした")
        else:
            self._set_status(f"{count} 件ハイライトしました")

    def _find(self, direction: str):
        needle = self.search_var.get()
        if not needle:
            self._set_status("検索語が空です")
            return

        # 既存選択/ハイライトは残してもいいが、ジャンプ用に match は更新
        self.text.tag_remove("match", "1.0", "end")

        if direction == "next":
            start = self.text.index("insert")
            idx = self.text.search(needle, start, stopindex="end", nocase=0)
            if not idx:
                # 先頭に巻き戻し
                idx = self.text.search(needle, "1.0", stopindex="end", nocase=0)
        else:
            # prev：現在位置より前を探す
            start = self.text.index("insert")
            idx = self.text.search(needle, start, stopindex="1.0", backwards=True, nocase=0)
            if not idx:
                # 末尾に巻き戻し
                idx = self.text.search(needle, "end", stopindex="1.0", backwards=True, nocase=0)

        if not idx:
            self._set_status("見つかりませんでした")
            return

        end = f"{idx}+{len(needle)}c"
        self.text.tag_add("match", idx, end)

        # 選択してジャンプ
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_add("sel", idx, end)
        self.text.mark_set("insert", end if direction == "next" else idx)
        self.text.see(idx)

        self._set_status(f"移動: {idx}")

    def find_next(self):
        self._find("next")

    def find_prev(self):
        self._find("prev")

    # ---------- helpers ----------
    def _set_status(self, msg: str):
        self.status_var.set(msg)

    def _update_title(self, dirty: bool | None = None):
        name = self.filepath or self.autosave_path
        base = os.path.basename(name)

        # dirty表示：呼び出し側が指定しない場合はModifiedで推測（完全ではないが見た目用）
        if dirty is None:
            dirty = False

        dirty_mark = " *" if dirty else ""
        save_state = ""
        if self._last_save_ts:
            save_state = f"（最終保存 {self._last_save_ts}）"
        if not self._last_save_ok:
            save_state = "（保存失敗）"

        self.title(f"Pythonメモ帳 - {base}{dirty_mark} {save_state}")

if __name__ == "__main__":
    app = Notepad()
    app.mainloop()
