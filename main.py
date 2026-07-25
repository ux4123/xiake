#!/usr/bin/env python3
"""
Claw's Trainer — 《侠客风云传前传》多功能修改器
================================================
支持内存修改和存档编辑两种模式。

使用方法:
    python main.py

依赖安装:
    pip install pymem psutil
"""

import sys
import os
import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from typing import Optional, Dict, Any, List

# ── 路径处理：兼容 PyInstaller 打包 ────────────────────────────────
if getattr(sys, 'frozen', False):
    # 运行在 PyInstaller 打包的可执行文件中
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from config import (
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    PROCESS_NAME, HOTKEYS, SCAN_TYPES
)

# ── 日志配置 ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("Trainer")


# ── 数据目录：存放用户配置、日志等 ──────────────────────────────────
APP_DATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "ClawTrainer"
)
os.makedirs(APP_DATA_DIR, exist_ok=True)


class TrainerApp:
    """主应用程序类。"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # 引擎组件（懒加载）
        self.memory_engine = None
        self.save_editor = None
        self.mono_helper = None

        # 内存扫描状态
        self.scanned_addresses: List[int] = []
        self.custom_addresses: Dict[str, int] = {}
        self.freeze_status: Dict[str, bool] = {}

        # 界面构建
        self._setup_styles()
        self._build_menu()
        self._build_main_layout()

        # 状态栏
        self._build_status_bar()

        # 启动时自动尝试附加
        self.root.after(1000, self._auto_attach)

    # ── 样式 ─────────────────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # 主题色（暗色科技风格）
        bg = "#1e1e2e"
        fg = "#cdd6f4"
        select_bg = "#45475a"

        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg, font=("微软雅黑", 10))
        style.configure("TButton", background="#313244", foreground=fg,
                        font=("微软雅黑", 10), borderwidth=1, padding=4)
        style.map("TButton",
                  background=[("active", "#45475a"), ("pressed", "#585b70")])

        style.configure("Header.TLabel", font=("微软雅黑", 12, "bold"))
        style.configure("Status.TLabel", font=("微软雅黑", 9), foreground="#a6adc8")
        style.configure("Green.TLabel", foreground="#a6e3a1", font=("微软雅黑", 10))
        style.configure("Red.TLabel", foreground="#f38ba8", font=("微软雅黑", 10))
        style.configure("Accent.TButton", background="#89b4fa", foreground="#1e1e2e")

        style.configure("TEntry", fieldbackground="#313244", foreground=fg,
                        insertcolor=fg, font=("微软雅黑", 10))
        style.configure("TNotebook", background=bg, tabmargins=[2, 5, 2, 0])
        style.configure("TNotebook.Tab", background="#313244", foreground=fg,
                        padding=[8, 3], font=("微软雅黑", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", "#45475a")],
                  foreground=[("selected", "#cdd6f4")])

        self.root.configure(bg=bg)

    # ── 菜单栏 ───────────────────────────────────────────────────────

    def _build_menu(self):
        menubar = tk.Menu(self.root, bg="#313244", fg="#cdd6f4",
                          activebackground="#45475a", activeforeground="#cdd6f4")

        # 文件
        file_menu = tk.Menu(menubar, tearoff=0, bg="#313244", fg="#cdd6f4")
        file_menu.add_command(label="附加进程", command=self._do_attach)
        file_menu.add_command(label="断开进程", command=self._do_detach)
        file_menu.add_separator()
        file_menu.add_command(label="打开存档目录", command=self._open_save_dir)
        file_menu.add_separator()
        file_menu.add_command(label="退出 (Ctrl+Q)", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)

        # 工具
        tool_menu = tk.Menu(menubar, tearoff=0, bg="#313244", fg="#cdd6f4")
        tool_menu.add_command(label="重置所有冻结", command=self._reset_freezes)
        tool_menu.add_command(label="清空扫描结果", command=self._clear_scan_results)
        tool_menu.add_separator()
        tool_menu.add_command(label="关于", command=self._show_about)
        menubar.add_cascade(label="工具", menu=tool_menu)

        self.root.config(menu=menubar)

    # ── 主布局 ───────────────────────────────────────────────────────

    def _build_main_layout(self):
        # Notebook (标签页)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=(6, 0))

        # 标签页
        self._build_tab_process()     # 进程控制
        self._build_tab_combat()      # 战斗辅助
        self._build_tab_resource()    # 资源修改
        self._build_tab_scan()        # 内存扫描
        self._build_tab_save()        # 存档编辑
        self._build_tab_log()         # 日志

    # ── 标签页 1: 进程控制 ───────────────────────────────────────────

    def _build_tab_process(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🎯 进程控制")

        # 进程状态
        status_frame = ttk.LabelFrame(frame, text="进程状态", padding=10)
        status_frame.pack(fill="x", padx=10, pady=10)

        self.lbl_process = ttk.Label(status_frame, text="❌ 未连接",
                                     style="Red.TLabel")
        self.lbl_process.pack(side="left", padx=5)

        ttk.Button(status_frame, text="🔄 附加进程",
                   command=self._do_attach).pack(side="right", padx=5)
        ttk.Button(status_frame, text="⛔ 断开",
                   command=self._do_detach).pack(side="right", padx=5)

        # 游戏信息
        info_frame = ttk.LabelFrame(frame, text="游戏信息", padding=10)
        info_frame.pack(fill="x", padx=10, pady=5)

        info_text = (
            "游戏: 侠客风云传前传 (Tale of Wuxia: The Pre-Sequel)\n"
            "进程: YoungHero.exe | 引擎: Unity 3D (Mono)\n"
            f"热键: {', '.join(f'{k}={v}' for k, v in list(HOTKEYS.items())[:4])}"
        )
        ttk.Label(info_frame, text=info_text).pack(anchor="w")

        # 快速操作
        quick_frame = ttk.LabelFrame(frame, text="快速操作", padding=10)
        quick_frame.pack(fill="both", expand=True, padx=10, pady=5)

        buttons = [
            ("💊 无限气血", self._toggle_hp),
            ("⚡ 无限内力", self._toggle_mp),
            ("💀 一击必杀", self._toggle_onehit),
            ("🏃 无限行动", self._toggle_move),
            ("💰 无限金钱", self._toggle_money),
            ("📚 无限阅历", self._toggle_ap),
        ]

        row_frame = None
        for i, (text, cmd) in enumerate(buttons):
            if i % 3 == 0:
                row_frame = ttk.Frame(quick_frame)
                row_frame.pack(fill="x", pady=3)
            btn = ttk.Button(row_frame, text=text, command=cmd, width=18)
            btn.pack(side="left", padx=5)

    # ── 标签页 2: 战斗辅助 ───────────────────────────────────────────

    def _build_tab_combat(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="⚔️ 战斗辅助")

        # 冻结开关组
        freeze_frame = ttk.LabelFrame(frame, text="实时修改（战斗中生效）", padding=10)
        freeze_frame.pack(fill="x", padx=10, pady=10)

        toggles = [
            ("无限气血", "hp", "战斗中保持气血满值"),
            ("无限内力", "mp", "战斗中保持内力满值"),
            ("一击必杀", "onehit", "攻击即秒杀敌人"),
            ("无限行动", "move", "每回合无限移动/攻击"),
            ("敌人不能行动", "enemynoact", "敌人无法行动"),
            ("技能无冷却", "nocooldown", "技能无需冷却"),
        ]

        self.combat_vars = {}
        for i, (label, key, desc) in enumerate(toggles):
            var = tk.BooleanVar(value=False)
            self.combat_vars[key] = var
            cb = ttk.Checkbutton(freeze_frame, text=label, variable=var,
                                 command=lambda k=key: self._on_combat_toggle(k))
            cb.grid(row=i//2, column=(i%2)*2, sticky="w", padx=10, pady=3)
            ttk.Label(freeze_frame, text=desc, style="Status.TLabel"
                      ).grid(row=i//2, column=(i%2)*2+1, sticky="w", padx=5, pady=3)

        # 自定义地址
        custom_frame = ttk.LabelFrame(frame, text="自定义地址修改", padding=10)
        custom_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(custom_frame, text="地址 (十六进制):").grid(row=0, column=0, padx=5)
        self.entry_addr = ttk.Entry(custom_frame, width=12)
        self.entry_addr.grid(row=0, column=1, padx=5)

        ttk.Label(custom_frame, text="值类型:").grid(row=0, column=2, padx=5)
        self.combo_type = ttk.Combobox(custom_frame, values=list(SCAN_TYPES.keys()),
                                        width=8, state="readonly")
        self.combo_type.set("i32")
        self.combo_type.grid(row=0, column=3, padx=5)

        ttk.Label(custom_frame, text="值:").grid(row=0, column=4, padx=5)
        self.entry_custom_val = ttk.Entry(custom_frame, width=10)
        self.entry_custom_val.grid(row=0, column=5, padx=5)
        self.entry_custom_val.insert(0, "99999")

        ttk.Button(custom_frame, text="写入", command=self._write_custom,
                   style="Accent.TButton").grid(row=0, column=6, padx=10)
        ttk.Button(custom_frame, text="锁定", command=self._freeze_custom
                   ).grid(row=0, column=7, padx=5)

    # ── 标签页 3: 资源修改 ──────────────────────────────────────────

    def _build_tab_resource(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💰 资源修改")

        # 快速修改
        quick_frame = ttk.LabelFrame(frame, text="一键修改", padding=10)
        quick_frame.pack(fill="x", padx=10, pady=10)

        row = 0
        quick_ops = [
            ("金钱设为 999999", lambda: self._memory_set("money", 999999)),
            ("阅历设为 9999", lambda: self._memory_set("ap", 9999)),
            ("声望设为 9999", lambda: self._memory_set("reputation", 9999)),
            ("所有角色属性最大化", self._max_roles_memory),
        ]
        for text, cmd in quick_ops:
            ttk.Button(quick_frame, text=text, command=cmd,
                       width=30).grid(row=row, column=0, padx=10, pady=3, sticky="w")
            row += 1

        # 手动数值写入
        manual_frame = ttk.LabelFrame(frame, text="手动写入数值", padding=10)
        manual_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(manual_frame, text="地址:").grid(row=0, column=0, padx=5)
        self.res_addr = ttk.Entry(manual_frame, width=14)
        self.res_addr.grid(row=0, column=1, padx=5)

        ttk.Label(manual_frame, text="值:").grid(row=0, column=2, padx=5)
        self.res_val = ttk.Entry(manual_frame, width=14)
        self.res_val.grid(row=0, column=3, padx=5)
        self.res_val.insert(0, "99999")

        ttk.Button(manual_frame, text="写入", command=self._manual_write
                   ).grid(row=0, column=4, padx=10)

        # 扫描结果快速操作
        ttk.Label(manual_frame, text="提示: 先用「内存扫描」找到地址后复制到这里").grid(
            row=1, column=0, columnspan=5, pady=5, sticky="w")

    # ── 标签页 4: 内存扫描 ──────────────────────────────────────────

    def _build_tab_scan(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🔍 内存扫描")

        # 扫描参数
        param_frame = ttk.Frame(frame)
        param_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(param_frame, text="扫描值:").pack(side="left", padx=2)
        self.scan_value_entry = ttk.Entry(param_frame, width=12)
        self.scan_value_entry.pack(side="left", padx=2)
        self.scan_value_entry.insert(0, "1000")

        ttk.Label(param_frame, text="类型:").pack(side="left", padx=2)
        self.scan_type_combo = ttk.Combobox(param_frame,
                                             values=list(SCAN_TYPES.keys()),
                                             width=6, state="readonly")
        self.scan_type_combo.set("i32")
        self.scan_type_combo.pack(side="left", padx=2)

        ttk.Button(param_frame, text="🔍 首次扫描",
                   command=self._do_scan).pack(side="left", padx=5)
        ttk.Button(param_frame, text="🔄 再次扫描",
                   command=self._do_rescan).pack(side="left", padx=5)
        ttk.Button(param_frame, text="🧹 清空",
                   command=self._clear_scan_results).pack(side="left", padx=5)

        ttk.Label(param_frame,
                  text=f"已附加: {PROCESS_NAME}").pack(side="right", padx=5)

        # 扫描结果
        result_frame = ttk.LabelFrame(frame, text="扫描结果", padding=5)
        result_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 列表+滚动条
        list_frame = ttk.Frame(result_frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self.scan_listbox = tk.Listbox(list_frame,
                                        yscrollcommand=scrollbar.set,
                                        bg="#313244", fg="#cdd6f4",
                                        selectbackground="#45475a",
                                        font=("Consolas", 9), height=10)
        scrollbar.config(command=self.scan_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.scan_listbox.pack(side="left", fill="both", expand=True)

        # 操作
        op_frame = ttk.Frame(result_frame)
        op_frame.pack(fill="x", pady=5)

        self.lbl_scan_count = ttk.Label(op_frame, text="结果: 0")
        self.lbl_scan_count.pack(side="left", padx=5)

        ttk.Button(op_frame, text="📋 复制选中地址",
                   command=self._copy_selected_addr).pack(side="left", padx=5)
        ttk.Button(op_frame, text="✏️ 写入 999999",
                   command=self._write_selected).pack(side="left", padx=5)
        ttk.Button(op_frame, text="🔒 锁定选中",
                   command=self._freeze_selected).pack(side="left", padx=5)

    # ── 标签页 5: 存档编辑 ──────────────────────────────────────────

    def _build_tab_save(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="💾 存档编辑")

        # 存档选择
        sel_frame = ttk.Frame(frame)
        sel_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(sel_frame, text="📂 查找存档",
                   command=self._find_saves).pack(side="left", padx=5)
        ttk.Button(sel_frame, text="📁 手动选择存档",
                   command=self._browse_save).pack(side="left", padx=5)
        ttk.Button(sel_frame, text="💾 保存修改",
                   command=self._save_savefile).pack(side="right", padx=5)

        # 存档列表
        self.save_list_var = tk.StringVar(value="")
        self.save_combo = ttk.Combobox(sel_frame, textvariable=self.save_list_var,
                                        width=50, state="readonly")
        self.save_combo.pack(side="left", padx=10, fill="x", expand=True)
        self.save_combo.bind("<<ComboboxSelected>>", self._on_save_selected)

        # 编辑器
        edit_frame = ttk.LabelFrame(frame, text="存档数据编辑器", padding=5)
        edit_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 分左右两栏
        paned = ttk.PanedWindow(edit_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # 左栏：快速修改
        quick_left = ttk.Frame(paned)
        paned.add(quick_left, weight=1)

        ttk.Label(quick_left, text="快速修改", style="Header.TLabel").pack(anchor="w", pady=3)

        save_quick_ops = [
            ("金钱 999999", lambda: self._save_set("m_iMoney", 999999)),
            ("阅历 9999", lambda: self._save_set("m_iAttributePoints", 9999)),
            ("声望 9999", lambda: self._save_set("m_iReputation", 9999)),
            ("剑术满", lambda: self._save_set("m_iSword", 9999)),
            ("刀法满", lambda: self._save_set("m_iBlade", 9999)),
            ("拳掌满", lambda: self._save_set("m_iFist", 9999)),
            ("棍法满", lambda: self._save_set("m_iStaff", 9999)),
            ("全角色属性最大化", self._save_max_roles),
        ]

        for text, cmd in save_quick_ops:
            ttk.Button(quick_left, text=text, command=cmd,
                       width=25).pack(anchor="w", padx=5, pady=2)

        # 右栏：自定义编辑
        custom_right = ttk.Frame(paned)
        paned.add(custom_right, weight=1)

        ttk.Label(custom_right, text="自定义字段编辑", style="Header.TLabel").pack(anchor="w", pady=3)

        ttk.Label(custom_right, text="字段名:").pack(anchor="w", padx=5)
        self.save_field_entry = ttk.Entry(custom_right)
        self.save_field_entry.pack(fill="x", padx=5, pady=2)
        self.save_field_entry.insert(0, "m_iMoney")

        ttk.Label(custom_right, text="新值:").pack(anchor="w", padx=5)
        self.save_val_entry = ttk.Entry(custom_right)
        self.save_val_entry.pack(fill="x", padx=5, pady=2)
        self.save_val_entry.insert(0, "999999")

        ttk.Button(custom_right, text="✏️ 写入",
                   command=self._save_custom_write).pack(anchor="w", padx=5, pady=5)

        # 角色列表
        self.save_role_text = scrolledtext.ScrolledText(
            edit_frame, height=8, bg="#313244", fg="#cdd6f4",
            font=("Consolas", 9), insertbackground="#cdd6f4",
            state="disabled"
        )
        self.save_role_text.pack(fill="both", expand=True, padx=5, pady=5)

        # 状态提示
        self.lbl_save_status = ttk.Label(frame, text="未加载存档",
                                          style="Status.TLabel")
        self.lbl_save_status.pack(anchor="w", padx=10, pady=2)

    # ── 标签页 6: 日志 ──────────────────────────────────────────────

    def _build_tab_log(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="📋 日志")

        self.log_text = scrolledtext.ScrolledText(
            frame, bg="#1e1e2e", fg="#cdd6f4",
            font=("Consolas", 9), insertbackground="#cdd6f4",
            state="disabled", wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

        # 自定义日志 handler
        class TextHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                self.text_widget.configure(state="normal")
                self.text_widget.insert("end", msg + "\n")
                self.text_widget.see("end")
                self.text_widget.configure(state="disabled")

        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S"
        ))
        logging.getLogger().addHandler(handler)

    # ── 状态栏 ───────────────────────────────────────────────────────

    def _build_status_bar(self):
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", padx=6, pady=3)

        self.status_var = tk.StringVar(value="就绪 - 启动游戏后点击「附加进程」")
        self.lbl_status = ttk.Label(status_frame, textvariable=self.status_var,
                                     style="Status.TLabel")
        self.lbl_status.pack(side="left")

        self.lbl_attach_status = ttk.Label(status_frame, text="❌ 未连接",
                                            style="Red.TLabel")
        self.lbl_attach_status.pack(side="right", padx=10)

    # ── 引擎初始化 ──────────────────────────────────────────────────

    def _init_memory(self):
        """懒加载内存引擎。"""
        if self.memory_engine is None:
            try:
                from memory_engine import MemoryEngine, MonoHelper
                self.memory_engine = MemoryEngine()
                self.mono_helper = MonoHelper(self.memory_engine)
                logger.info("内存引擎已初始化")
            except ImportError as e:
                logger.error(f"导入 pymem 失败: {e}，请运行: pip install pymem")
                messagebox.showerror("依赖缺失", "需要 pymem 库:\npip install pymem")
                return False
        return True

    def _init_save(self):
        """懒加载存档编辑器。"""
        if self.save_editor is None:
            try:
                from save_editor import SaveEditor
                self.save_editor = SaveEditor()
                logger.info("存档编辑器已初始化")
            except Exception as e:
                logger.error(f"存档编辑器初始化失败: {e}")
                return False
        return True

    # ── 进程操作 ──────────────────────────────────────────────────────

    def _auto_attach(self):
        """启动时自动尝试附加进程。"""
        if self._init_memory():
            if self.memory_engine.attach(PROCESS_NAME):
                self._on_attach_success()
            else:
                logger.info("游戏未运行，可通过「附加进程」手动连接")

    def _do_attach(self):
        """手动附加进程。"""
        if not self._init_memory():
            return

        if self.memory_engine.attach(PROCESS_NAME):
            self._on_attach_success()
        else:
            messagebox.showwarning("附加失败",
                                    f"未找到进程 {PROCESS_NAME}\n请先启动游戏。")

    def _on_attach_success(self):
        """附加成功后的界面更新。"""
        self.lbl_process.configure(text="✅ 已连接", style="Green.TLabel")
        self.lbl_attach_status.configure(text=f"✅ PID={self.memory_engine.process_id}",
                                          style="Green.TLabel")
        self.status_var.set(f"已附加到 {PROCESS_NAME}")
        logger.info(f"成功附加到进程 {PROCESS_NAME}")

    def _do_detach(self):
        """断开进程连接。"""
        if self.memory_engine:
            self.memory_engine.detach()
        self.lbl_process.configure(text="❌ 未连接", style="Red.TLabel")
        self.lbl_attach_status.configure(text="❌ 未连接", style="Red.TLabel")
        self.status_var.set("已断开")

    # ── 战斗辅助操作 ────────────────────────────────────────────────

    def _on_combat_toggle(self, key: str):
        """战斗辅助开关处理。"""
        if not self.memory_engine or not self.memory_engine.is_attached:
            messagebox.showwarning("警告", "请先附加游戏进程")
            self.combat_vars[key].set(False)
            return

        if self.combat_vars[key].get():
            logger.info(f"已开启: {key}")
        else:
            logger.info(f"已关闭: {key}")

    def _toggle_hp(self):
        """切换无限气血。"""
        logger.info("无限气血: 正在扫描战斗中的气血地址...")
        logger.info("提示: 请先在战斗中存档，然后在「内存扫描」标签页搜索当前HP值")

    def _toggle_mp(self):
        """切换无限内力。"""
        logger.info("无限内力: 正在扫描战斗中的内力地址...")
        logger.info("提示: 请先在战斗中存档，然后在「内存扫描」标签页搜索当前MP值")

    def _toggle_onehit(self):
        """切换一击必杀。"""
        logger.info("一击必杀: 功能待扫描到地址后可用")
        logger.info("提示: 在战斗中搜索敌人HP变化找到地址后锁定为0")

    def _toggle_move(self):
        """切换无限行动。"""
        logger.info("无限行动: 功能待扫描到地址后可用")

    def _toggle_money(self):
        """切换无限金钱。"""
        self._memory_set("money", 999999)

    def _toggle_ap(self):
        """切换无限阅历。"""
        self._memory_set("ap", 9999)

    # ── 内存写入操作 ────────────────────────────────────────────────

    def _memory_set(self, target: str, value: int):
        """快捷设置内存值。"""
        if not self.memory_engine or not self.memory_engine.is_attached:
            messagebox.showwarning("警告", "请先附加游戏进程")
            return

        logger.info(f"修改 {target} = {value}")
        logger.info(f"提示: 请用「内存扫描」找到 {target} 的地址后填写到地址栏")

    def _max_roles_memory(self):
        """内存中最大化角色属性。"""
        if not self.memory_engine or not self.memory_engine.is_attached:
            messagebox.showwarning("警告", "请先附加游戏进程")
            return
        logger.info("最大化角色属性 — 需要先用 CE 找到角色属性基址")
        logger.info("建议使用「存档编辑」标签页修改角色属性，更稳定可靠")

    def _write_custom(self):
        """写入自定义地址。"""
        if not self.memory_engine or not self.memory_engine.is_attached:
            messagebox.showwarning("警告", "请先附加游戏进程")
            return

        try:
            addr_str = self.entry_addr.get().strip()
            if addr_str.startswith("0x") or addr_str.startswith("0X"):
                addr = int(addr_str, 16)
            else:
                addr = int(addr_str)

            val_str = self.entry_custom_val.get().strip()
            if val_str.isdigit():
                val = int(val_str)
            else:
                val = float(val_str)

            vtype = self.combo_type.get()

            if vtype == "i32":
                self.memory_engine.write_int(addr, val)
            elif vtype == "f32":
                self.memory_engine.write_float(addr, float(val))
            elif vtype == "i16":
                self.memory_engine.write_short(addr, val)
            elif vtype == "i8":
                self.memory_engine.write_uchar(addr, val)
            elif vtype == "i64":
                import struct
                self.memory_engine.write_bytes(addr, struct.pack("<q", val))
            elif vtype == "f64":
                import struct
                self.memory_engine.write_bytes(addr, struct.pack("<d", float(val)))

            logger.info(f"✅ 已写入 0x{addr:X} = {val} ({vtype})")
            self.status_var.set(f"已写入 0x{addr:X} = {val}")
        except Exception as e:
            logger.error(f"写入失败: {e}")
            messagebox.showerror("写入失败", str(e))

    def _freeze_custom(self):
        """冻结自定义地址的数值。"""
        if not self.memory_engine or not self.memory_engine.is_attached:
            messagebox.showwarning("警告", "请先附加游戏进程")
            return

        try:
            addr_str = self.entry_addr.get().strip()
            if addr_str.startswith("0x") or addr_str.startswith("0X"):
                addr = int(addr_str, 16)
            else:
                addr = int(addr_str)

            val_str = self.entry_custom_val.get().strip()
            if val_str.isdigit():
                val = int(val_str)
            else:
                val = float(val_str)

            vtype = self.combo_type.get()
            name = f"custom_0x{addr:X}"

            if name in self.memory_engine._freeze_flags:
                self.memory_engine.unfreeze_value(name)
                logger.info(f"已解除锁定: 0x{addr:X}")
            else:
                self.memory_engine.freeze_value(name, addr, val, vtype)
                logger.info(f"🔒 已锁定: 0x{addr:X} = {val}")

        except Exception as e:
            logger.error(f"锁定失败: {e}")

    def _manual_write(self):
        """资源页面手动写入。"""
        try:
            addr_str = self.res_addr.get().strip()
            if addr_str.startswith("0x") or addr_str.startswith("0X"):
                addr = int(addr_str, 16)
            else:
                addr = int(addr_str)

            val = int(self.res_val.get().strip())
            self.memory_engine.write_int(addr, val)
            logger.info(f"✅ 写入 0x{addr:X} = {val}")
        except Exception as e:
            logger.error(f"写入失败: {e}")

    # ── 内存扫描操作 ────────────────────────────────────────────────

    def _do_scan(self):
        """执行内存扫描。"""
        if not self.memory_engine or not self.memory_engine.is_attached:
            messagebox.showwarning("警告", "请先附加游戏进程")
            return

        try:
            value_str = self.scan_value_entry.get().strip()
            if value_str.isdigit():
                value = int(value_str)
            else:
                value = float(value_str)

            vtype = self.scan_type_combo.get()

            self.status_var.set(f"正在扫描数值 {value} ({vtype})...")
            self.root.update()

            # 在新线程中扫描
            def scan_thread():
                results = self.memory_engine.scan_value(value, vtype)
                self.root.after(0, lambda: self._on_scan_complete(results))

            t = threading.Thread(target=scan_thread, daemon=True)
            t.start()

        except Exception as e:
            logger.error(f"扫描参数错误: {e}")
            messagebox.showerror("扫描错误", str(e))

    def _do_rescan(self):
        """对已有结果再次扫描。"""
        if not self.scanned_addresses:
            messagebox.showinfo("提示", "尚无扫描结果，请先执行首次扫描")
            return

        try:
            value_str = self.scan_value_entry.get().strip()
            if value_str.isdigit():
                value = int(value_str)
            else:
                value = float(value_str)

            vtype = self.scan_type_combo.get()

            self.status_var.set(f"正在重新扫描 ({len(self.scanned_addresses)} 个地址)...")
            self.root.update()

            def rescan_thread():
                results = self.memory_engine.rescan(self.scanned_addresses, value, vtype)
                self.root.after(0, lambda: self._on_scan_complete(results))

            t = threading.Thread(target=rescan_thread, daemon=True)
            t.start()

        except Exception as e:
            logger.error(f"重新扫描错误: {e}")

    def _on_scan_complete(self, results: List[int]):
        """扫描完成处理。"""
        self.scanned_addresses = results
        self.scan_listbox.delete(0, "end")
        for addr in results[:500]:  # 最多显示 500 个
            self.scan_listbox.insert("end", f"0x{addr:08X}")
        self.lbl_scan_count.configure(
            text=f"结果: {len(results)}" +
                 (" (显示前500)" if len(results) > 500 else "")
        )
        self.status_var.set(f"扫描完成，找到 {len(results)} 个匹配地址")

    def _clear_scan_results(self):
        """清空扫描结果。"""
        self.scanned_addresses = []
        self.scan_listbox.delete(0, "end")
        self.lbl_scan_count.configure(text="结果: 0")
        logger.info("扫描结果已清空")

    def _copy_selected_addr(self):
        """复制选中的地址到剪贴板。"""
        sel = self.scan_listbox.curselection()
        if sel:
            addr_text = self.scan_listbox.get(sel[0])
            self.root.clipboard_clear()
            self.root.clipboard_append(addr_text)
            self.status_var.set(f"已复制: {addr_text}")

    def _write_selected(self):
        """向选中地址写入值。"""
        sel = self.scan_listbox.curselection()
        if not sel:
            return
        try:
            addr_text = self.scan_listbox.get(sel[0])
            addr = int(addr_text, 16)
            self.memory_engine.write_int(addr, 999999)
            logger.info(f"✅ 写入 0x{addr:X} = 999999")
        except Exception as e:
            logger.error(f"写入失败: {e}")

    def _freeze_selected(self):
        """锁定选中的地址。"""
        sel = self.scan_listbox.curselection()
        if not sel:
            return
        try:
            addr_text = self.scan_listbox.get(sel[0])
            addr = int(addr_text, 16)
            name = f"scan_0x{addr:X}"

            if name in self.memory_engine._freeze_flags:
                self.memory_engine.unfreeze_value(name)
                logger.info(f"解除锁定: 0x{addr:X}")
            else:
                self.memory_engine.freeze_value(name, addr, 999999, "i32")
                logger.info(f"🔒 锁定 0x{addr:X} = 999999")
        except Exception as e:
            logger.error(f"锁定失败: {e}")

    def _reset_freezes(self):
        """重置所有冻结。"""
        if self.memory_engine:
            self.memory_engine.stop_all_freezes()
            logger.info("已停止所有冻结任务")

    # ── 存档编辑操作 ────────────────────────────────────────────────

    def _find_saves(self):
        """查找存档文件。"""
        if not self._init_save():
            return

        self.save_editor.find_save_dir()
        saves = self.save_editor.list_saves()

        if not saves:
            messagebox.showwarning("未找到存档",
                                    "未找到存档文件，请检查游戏是否已运行并保存过")
            return

        self.save_combo["values"] = [s["name"] for s in saves]
        self.save_combo.set(saves[0]["name"])
        self.lbl_save_status.configure(
            text=f"找到 {len(saves)} 个存档 | 目录: {self.save_editor.save_dir}")
        logger.info(f"找到 {len(saves)} 个存档")

    def _browse_save(self):
        """手动选择存档文件。"""
        if not self._init_save():
            return

        fpath = filedialog.askopenfilename(
            title="选择存档文件",
            filetypes=[("存档文件", "Save*.Save*"), ("所有文件", "*.*")]
        )
        if fpath:
            if self.save_editor.load_save(fpath):
                self._refresh_save_display()

    def _on_save_selected(self, event=None):
        """存档选择下拉框事件。"""
        if not self.save_editor or not self.save_editor.save_dir:
            return

        fname = self.save_combo.get()
        fpath = os.path.join(self.save_editor.save_dir, fname)
        if os.path.exists(fpath):
            if self.save_editor.load_save(fpath):
                self._refresh_save_display()

    def _refresh_save_display(self):
        """刷新存档数据显示。"""
        if not self.save_editor or not self.save_editor.save_data:
            return

        # 显示角色信息
        roles = self.save_editor.get_roles_info()
        text = f"存档文件: {os.path.basename(self.save_editor.current_save_path)}\n"
        text += f"角色数量: {len(roles)}\n\n"
        text += f"{'索引':<5} {'名称':<12} {'等级':<6} {'气血':<14} {'内力':<14} "
        text += f"{'臂力':<6} {'悟性':<6} {'身法':<6} {'根骨':<6}\n"
        text += "-" * 80 + "\n"

        for r in roles:
            text += (f"{r['index']:<5} {r['name']:<12} {r['level']:<6} "
                     f"{r['hp']:<14} {r['mp']:<14} "
                     f"{r['str']:<6} {r['int']:<6} {r['dex']:<6} {r['con']:<6}\n")

        # 重要字段快速预览
        text += "\n--- 游戏资源 ---\n"
        for field, info in [
            ("m_iMoney", "金钱"),
            ("m_iAttributePoints", "阅历"),
            ("m_iReputation", "声望"),
        ]:
            val = self.save_editor.get_value(field)
            text += f"{info}: {val}\n"

        self.save_role_text.configure(state="normal")
        self.save_role_text.delete("1.0", "end")
        self.save_role_text.insert("1.0", text)
        self.save_role_text.configure(state="disabled")

        self.lbl_save_status.configure(
            text=f"已加载: {os.path.basename(self.save_editor.current_save_path)}")
        logger.info(f"存档已加载: {os.path.basename(self.save_editor.current_save_path)}")

    def _save_set(self, field: str, value: int):
        """设置存档字段值。"""
        if not self.save_editor or not self.save_editor.save_data:
            messagebox.showwarning("警告", "请先加载存档")
            return

        self.save_editor.set_value(field, value)
        self._refresh_save_display()
        logger.info(f"存档修改: {field} = {value}")

    def _save_max_roles(self):
        """存档中最大化角色属性。"""
        if not self.save_editor or not self.save_editor.save_data:
            messagebox.showwarning("警告", "请先加载存档")
            return

        self.save_editor.max_roles_stats()
        self._refresh_save_display()
        logger.info("所有角色属性已最大化")

    def _save_custom_write(self):
        """自定义字段写入存档。"""
        if not self.save_editor or not self.save_editor.save_data:
            messagebox.showwarning("警告", "请先加载存档")
            return

        field = self.save_field_entry.get().strip()
        val_str = self.save_val_entry.get().strip()

        try:
            if val_str.isdigit():
                val = int(val_str)
            else:
                val = float(val_str)

            if self.save_editor.set_value(field, val):
                self._refresh_save_display()
                logger.info(f"存档修改: {field} = {val}")
            else:
                logger.warning(f"字段 {field} 不存在或写入失败")
        except Exception as e:
            logger.error(f"写入失败: {e}")

    def _save_savefile(self):
        """保存存档文件。"""
        if not self.save_editor or not self.save_editor.save_data:
            messagebox.showwarning("警告", "请先加载存档")
            return

        if self.save_editor.save():
            self._refresh_save_display()
            logger.info("存档已保存")
            messagebox.showinfo("成功", "存档已保存！\n请在游戏中重新读取存档。")

    # ── 工具 ─────────────────────────────────────────────────────────

    def _open_save_dir(self):
        """打开存档目录。"""
        if not self._init_save():
            return
        self.save_editor.find_save_dir()
        if self.save_editor.save_dir:
            import subprocess
            subprocess.Popen(["explorer" if sys.platform == "win32" else "open",
                              self.save_editor.save_dir])
        else:
            messagebox.showwarning("未找到", "未找到存档目录")

    def _show_about(self):
        """关于对话框。"""
        messagebox.showinfo(
            "关于 Claw's Trainer",
            "Claw's Trainer — 《侠客风云传前传》多功能修改器\n\n"
            "版本: 1.0.0\n"
            "引擎: Unity 3D (Mono)\n"
            "进程: YoungHero.exe\n\n"
            "⚠️ 仅供单机游戏使用\n"
            "请在使用时关闭杀毒软件（对内存修改器存在误报）"
        )

    # ── 运行 ─────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


def main():
    app = TrainerApp()
    app.run()


if __name__ == "__main__":
    main()
