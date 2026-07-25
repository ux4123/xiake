"""
《侠客风云传前传》修改器 - 配置文件
"""

import os

# ===== 游戏进程配置 =====
PROCESS_NAME = "YoungHero.exe"
GAME_WINDOW_TITLE = "侠客风云传前传"

# ===== 存档配置 =====
SAVE_DIR_CANDIDATES = [
    # Steam 版典型路径
    os.path.expandvars(r"%USERPROFILE%\Documents\Heluo\TaleOfWuxiaPre\Config\SaveData"),
    os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow\Heluo\TaleOfWuxiaPre\Config\SaveData"),
    # 凤凰游戏版
    os.path.expandvars(r"%ProgramFiles(x86)%\FHYX\Tale of Wuxia The Pre-Sequel\Config\SaveData"),
    os.path.expandvars(r"%ProgramFiles%\FHYX\Tale of Wuxia The Pre-Sequel\Config\SaveData"),
    # Steam 备用
    os.path.expandvars(r"%USERPROFILE%\Documents\My Games\Heluo\TaleOfWuxiaPre\Config\SaveData"),
]

SAVE_FILE_PREFIX = "Save"  # Save0.Save, Save1.Save ...

# ===== 默认内存扫描值类型 =====
SCAN_TYPES = {
    "i32": {"type": int, "size": 4, "label": "4字节整数"},
    "f32": {"type": float, "size": 4, "label": "4字节浮点"},
    "i16": {"type": int, "size": 2, "label": "2字节整数"},
    "i8":  {"type": int, "size": 1, "label": "1字节整数"},
    "i64": {"type": int, "size": 8, "label": "8字节整数"},
    "f64": {"type": float, "size": 8, "label": "双精度浮点"},
}

# ===== 默认热键 (virtual key codes) =====
HOTKEYS = {
    "无限气血": "F1",
    "无限内力": "F2",
    "一击必杀": "F3",
    "无限行动": "F4",
    "无限金钱": "F5",
    "超级速度": "F6",
    "技能无冷却": "F7",
    "物品不减": "F8",
}

# ===== 窗口配置 =====
WINDOW_TITLE = "Claw's Trainer — 侠客风云传前传"
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
WINDOW_MIN_WIDTH = 700
WINDOW_MIN_HEIGHT = 500
