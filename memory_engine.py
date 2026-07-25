"""
《侠客风云传前传》修改器 - 内存操作引擎

基于 pymem 实现进程附加、内存读写、数值扫描等功能。
由于游戏采用 Unity Mono 运行时，类实例在内存中有固定模式可循。
"""

import struct
import logging
import time
import threading
from typing import Optional, List, Tuple, Dict, Any, Callable

logger = logging.getLogger("MemoryEngine")


class MemoryEngine:
    """内存操作引擎——连接游戏进程并修改内存数据。"""

    def __init__(self):
        self.pm = None
        self.process_id = None
        self.is_attached = False
        self._freeze_threads: Dict[str, threading.Thread] = {}
        self._freeze_flags: Dict[str, threading.Event] = {}

    # ── 进程管理 ──────────────────────────────────────────────────────

    def attach(self, process_name: str = "YoungHero.exe") -> bool:
        """附加到指定游戏进程。"""
        try:
            import pymem
            self.pm = pymem.Pymem(process_name)
            self.process_id = self.pm.process_id
            self.is_attached = True
            logger.info(f"已附加到进程 {process_name} (PID={self.process_id})")
            return True
        except pymem.exception.ProcessNotFound:
            logger.warning(f"未找到进程 {process_name}，请先启动游戏")
            return False
        except pymem.exception.PymemError as e:
            logger.error(f"进程附加失败: {e}")
            return False
        except ImportError:
            logger.error("需要安装 pymem 库: pip install pymem")
            return False

    def detach(self):
        """断开与游戏进程的连接。"""
        if self.pm:
            self.stop_all_freezes()
            self.pm.close_process()
        self.pm = None
        self.process_id = None
        self.is_attached = False
        logger.info("已断开进程连接")

    # ── 内存读写 ──────────────────────────────────────────────────────

    def read_int(self, address: int) -> int:
        """读取 4 字节整数。"""
        return self.pm.read_int(address)

    def write_int(self, address: int, value: int):
        """写入 4 字节整数。"""
        self.pm.write_int(address, value)

    def read_float(self, address: int) -> float:
        """读取 4 字节浮点数。"""
        return self.pm.read_float(address)

    def write_float(self, address: int, value: float):
        """写入 4 字节浮点数。"""
        self.pm.write_float(address, value)

    def read_bytes(self, address: int, size: int) -> bytes:
        """读取指定长度的内存数据。"""
        return self.pm.read_bytes(address, size)

    def write_bytes(self, address: int, value: bytes):
        """写入内存数据。"""
        self.pm.write_bytes(address, value)

    def read_short(self, address: int) -> int:
        """读取 2 字节整数。"""
        return self.pm.read_short(address)

    def write_short(self, address: int, value: int):
        """写入 2 字节整数。"""
        self.pm.write_short(address, value)

    def read_uchar(self, address: int) -> int:
        """读取 1 字节无符号整数。"""
        return self.pm.read_uchar(address)

    def write_uchar(self, address: int, value: int):
        """写入 1 字节无符号整数。"""
        self.pm.write_uchar(address, value)

    # ── 基础扫描 ─────────────────────────────────────────────────────

    def scan_value(self, value: Any, value_type: str = "i32",
                   start_addr: int = None, end_addr: int = None) -> List[int]:
        """
        扫描内存中所有匹配指定值的地址。

        Args:
            value: 要扫描的值
            value_type: 值类型 ("i32", "f32", "i16", "i8", "i64", "f64")
            start_addr: 起始地址（默认模块基址）
            end_addr: 结束地址（默认模块基址+模块大小）

        Returns:
            匹配的地址列表
        """
        if not self.is_attached:
            return []

        try:
            module = self.pm.process_base.lpBaseOfDll
            module_size = self._get_module_size()

            if start_addr is None:
                start_addr = module
            if end_addr is None:
                end_addr = module + module_size

            logger.info(f"开始扫描数值 {value} ({value_type})，范围 0x{start_addr:X}-0x{end_addr:X}")

            results = []
            step = SCAN_TYPE_SIZE_MAP.get(value_type, 4)
            chunk_size = 4096

            for offset in range(0, end_addr - start_addr, chunk_size):
                try:
                    cur_addr = start_addr + offset
                    chunk = self.read_bytes(
                        cur_addr,
                        min(chunk_size + step - 1, end_addr - cur_addr)
                    )
                    for i in range(0, len(chunk) - step + 1):
                        addr = cur_addr + i
                        if self._check_value_at(chunk, i, value, value_type):
                            results.append(addr)
                except Exception:
                    continue

            logger.info(f"扫描完成，找到 {len(results)} 个匹配地址")
            return results

        except Exception as e:
            logger.error(f"扫描异常: {e}")
            return []

    def rescan(self, addresses: List[int], value: Any,
               value_type: str = "i32") -> List[int]:
        """从结果列表中过滤出仍匹配指定值的地址。"""
        if not self.is_attached:
            return []

        results = []
        for addr in addresses:
            try:
                current = self._read_typed(addr, value_type)
                if current == value:
                    results.append(addr)
            except Exception:
                continue
        return results

    # ── 指针链解析 ──────────────────────────────────────────────────

    def read_pointer(self, base_address: int, offsets: List[int]) -> Optional[int]:
        """
        解析多层指针链。

        Args:
            base_address: 基地址
            offsets: 偏移量数组，如 [0x0, 0x10, 0x2C]

        Returns:
            最终目标地址，或 None（出错时）
        """
        try:
            addr = base_address
            for offset in offsets:
                addr = self.read_int(addr)
                addr += offset
            return addr
        except Exception as e:
            logger.warning(f"指针解析失败: {e}")
            return None

    # ── AOB/特征码扫描 ────────────────────────────────────────────────

    def scan_pattern(self, pattern: bytes, mask: str = None,
                     start_addr: int = None, end_addr: int = None,
                     module_name: str = None) -> List[int]:
        """
        扫描 AOB 特征码。

        Args:
            pattern: 字节模式（如 b'\\x89\\x45\\x08\\x8B\\x45\\x08'）
            mask: 掩码字符串，'x' 表示匹配，'?' 表示任意（如 "xxxxxx"）
            start_addr: 起始地址
            end_addr: 结束地址
            module_name: 模块名（如不指定则扫描主模块）

        Returns:
            匹配的起始地址列表
        """
        if not self.is_attached:
            return []

        import pymem.pattern as pattern_module

        if module_name:
            module = pymem.process.module_from_name(
                self.pm.process_handle, module_name
            )
            if not module:
                logger.warning(f"未找到模块 {module_name}")
                return []
            start_addr = module.lpBaseOfDll
            end_addr = start_addr + module.SizeOfImage
        else:
            if start_addr is None:
                start_addr = self.pm.process_base.lpBaseOfDll
            if end_addr is None:
                end_addr = start_addr + self._get_module_size()

        try:
            if mask:
                matches = pattern_module.scan_pattern(
                    self.pm.process_handle,
                    start_addr, end_addr - start_addr,
                    pattern, mask
                )
            else:
                matches = pattern_module.scan_pattern(
                    self.pm.process_handle,
                    start_addr, end_addr - start_addr,
                    pattern, "x" * len(pattern)
                )
            return list(matches) if matches else []
        except Exception as e:
            logger.warning(f"AOB 扫描失败: {e}")
            return []

    # ── 数值冻结（锁定值） ────────────────────────────────────────────

    def freeze_value(self, name: str, address: int, value: Any,
                     value_type: str = "i32", interval: float = 0.1):
        """
        在后台线程中持续锁定指定地址的数值。

        Args:
            name: 冻结任务名称
            address: 目标地址
            value: 要锁定的值
            value_type: 值类型
            interval: 写入间隔（秒）
        """
        self.unfreeze_value(name)

        event = threading.Event()
        self._freeze_flags[name] = event

        def _freeze_loop():
            while not event.is_set():
                try:
                    if self.is_attached:
                        self._write_typed(address, value, value_type)
                except Exception:
                    pass
                event.wait(interval)

        t = threading.Thread(target=_freeze_loop, daemon=True,
                             name=f"Freeze-{name}")
        t.start()
        self._freeze_threads[name] = t
        logger.info(f"已启动数值冻结: {name} = {value} @ 0x{address:X}")

    def unfreeze_value(self, name: str):
        """停止指定名称的数值冻结任务。"""
        if name in self._freeze_flags:
            self._freeze_flags[name].set()
            self._freeze_flags.pop(name, None)
        self._freeze_threads.pop(name, None)

    def stop_all_freezes(self):
        """停止所有冻结任务。"""
        for name in list(self._freeze_flags.keys()):
            self.unfreeze_value(name)

    # ── 内部工具 ──────────────────────────────────────────────────────

    def _get_module_size(self) -> int:
        """获取主模块大小。"""
        return self.pm.process_base.SizeOfImage

    def _read_typed(self, address: int, value_type: str) -> Any:
        """按类型读取值。"""
        readers = {
            "i32": self.read_int,
            "f32": self.read_float,
            "i16": self.read_short,
            "i8":  self.read_uchar,
            "i64": lambda a: struct.unpack("<q", self.read_bytes(a, 8))[0],
            "f64": lambda a: struct.unpack("<d", self.read_bytes(a, 8))[0],
        }
        return readers.get(value_type, self.read_int)(address)

    def _write_typed(self, address: int, value: Any, value_type: str):
        """按类型写入值。"""
        writers = {
            "i32": self.write_int,
            "f32": self.write_float,
            "i16": self.write_short,
            "i8":  self.write_uchar,
            "i64": lambda a, v: self.write_bytes(a, struct.pack("<q", v)),
            "f64": lambda a, v: self.write_bytes(a, struct.pack("<d", v)),
        }
        writers.get(value_type, self.write_int)(address, value)

    @staticmethod
    def _check_value_at(data: bytes, offset: int, value: Any,
                        value_type: str) -> bool:
        """检查指定偏移处是否匹配目标值。"""
        try:
            if value_type == "i32":
                if offset + 4 > len(data):
                    return False
                return struct.unpack_from("<i", data, offset)[0] == value
            elif value_type == "f32":
                if offset + 4 > len(data):
                    return False
                return struct.unpack_from("<f", data, offset)[0] == value
            elif value_type == "i16":
                if offset + 2 > len(data):
                    return False
                return struct.unpack_from("<h", data, offset)[0] == value
            elif value_type == "i8":
                if offset + 1 > len(data):
                    return False
                return data[offset] == (value & 0xFF)
            elif value_type == "i64":
                if offset + 8 > len(data):
                    return False
                return struct.unpack_from("<q", data, offset)[0] == value
            elif value_type == "f64":
                if offset + 8 > len(data):
                    return False
                return struct.unpack_from("<d", data, offset)[0] == value
            return False
        except Exception:
            return False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.detach()


# ===== Unity Mono 辅助 =====

class MonoHelper:
    """
    Unity Mono 运行时辅助类。

    由于《侠客风云传前传》采用 Unity + Mono 编译模式，
    内存中的 C# 类实例包含类型信息，可以用 pymem 的
    Mono 功能枚举类和对象。
    """

    def __init__(self, memory_engine: MemoryEngine):
        self.me = memory_engine

    def find_class(self, class_name: str, namespace: str = "") -> Optional[Any]:
        """在 Mono 运行时中查找指定 C# 类。"""
        try:
            from pymem import Pymem
            # pymem 的 Mono 相关 API 通过 process 访问
            mono = self.me.pm.process
            if hasattr(mono, 'find_mono_class'):
                return mono.find_mono_class(class_name, namespace)
            return None
        except Exception as e:
            logger.warning(f"Mono 类查找失败 {class_name}: {e}")
            return None

    def find_static_field(self, class_name: str, field_name: str) -> Optional[int]:
        """查找 Mono 静态字段的内存地址。"""
        try:
            cls = self.find_class(class_name)
            if cls and hasattr(cls, 'get_static_field_address'):
                return cls.get_static_field_address(field_name)
            return None
        except Exception as e:
            logger.warning(f"Mono 静态字段查找失败 {field_name}: {e}")
            return None


# ===== 模块级常量 =====
SCAN_TYPE_SIZE_MAP = {
    "i32": 4, "f32": 4, "i16": 2,
    "i8": 1, "i64": 8, "f64": 8,
}

# ===== 游戏内存地址提示 =====
# 以下地址基于常见 Unity Mono 游戏的内存布局归纳。
# 实际地址可能随版本变化，建议先用 Cheat Engine 确认。
# 地址可通过训练器的"手动扫描"功能自动查找。

GAME_ADDRESS_HINTS = {
    "money": {
        "description": "金钱（4字节整数）",
        "type": "i32",
        "note": "先用 CE 扫描金钱值，找到稳定地址后填入"
    },
    "hp_current": {
        "description": "当前气血（4字节整数）",
        "type": "i32",
        "note": "战斗中搜索当前HP"
    },
    "hp_max": {
        "description": "最大气血（4字节整数）",
        "type": "i32",
        "note": "战斗中搜索最大HP"
    },
    "mp_current": {
        "description": "当前内力（4字节整数）",
        "type": "i32",
        "note": "战斗中搜索当前MP"
    },
    "mp_max": {
        "description": "最大内力（4字节整数）",
        "type": "i32",
        "note": "战斗中搜索最大MP"
    },
    "attack": {
        "description": "攻击力（4字节整数）",
        "type": "i32",
    },
    "defense": {
        "description": "防御力（4字节整数）",
        "type": "i32",
    },
    "move_range": {
        "description": "移动范围（4字节整数）",
        "type": "i32",
    },
}
