"""
《侠客风云传前传》修改器 - 存档编辑器

游戏存档为 JSON 明文格式，位于 Config\\SaveData\\ 目录下。
可直接读取、修改、写回。支持 Steam Cloud 同步。
"""

import json
import os
import shutil
import logging
import glob
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger("SaveEditor")

# ── 存档关键字段映射 ────────────────────────────────────────────────

SAVE_FIELDS = {
    # 玩家资源
    "m_iMoney": {
        "label": "金钱",
        "type": int,
        "category": "资源",
        "description": "队伍当前持有的金钱数量"
    },
    "m_iAttributePoints": {
        "label": "阅历",
        "type": int,
        "category": "资源",
        "description": "可用于学习功法的阅历点数"
    },
    "m_iReputation": {
        "label": "声望",
        "type": int,
        "category": "资源",
        "description": "江湖声望值"
    },
    "m_iSword": {
        "label": "剑术经验",
        "type": int,
        "category": "武艺",
        "description": "剑术修炼经验"
    },
    "m_iBlade": {
        "label": "刀法经验",
        "type": int,
        "category": "武艺",
        "description": "刀法修炼经验"
    },
    "m_iFist": {
        "label": "拳掌经验",
        "type": int,
        "category": "武艺",
        "description": "拳掌修炼经验"
    },
    "m_iStaff": {
        "label": "棍法经验",
        "type": int,
        "category": "武艺",
        "description": "棍法修炼经验"
    },
    "iLevel": {
        "label": "等级",
        "type": int,
        "category": "角色",
        "description": "角色等级"
    },
    "iExp": {
        "label": "经验值",
        "type": int,
        "category": "角色",
        "description": "当前经验值"
    },
    "iMaxHp": {
        "label": "最大气血",
        "type": int,
        "category": "角色",
        "description": "最大气血值"
    },
    "iHp": {
        "label": "当前气血",
        "type": int,
        "category": "角色",
        "description": "当前气血值"
    },
    "iMaxSp": {
        "label": "最大内力",
        "type": int,
        "category": "角色",
        "description": "最大内力值"
    },
    "iSp": {
        "label": "当前内力",
        "type": int,
        "category": "角色",
        "description": "当前内力值"
    },
    "iStr": {
        "label": "臂力",
        "type": int,
        "category": "属性",
        "description": "力量属性，影响攻击力"
    },
    "iInt": {
        "label": "悟性",
        "type": int,
        "category": "属性",
        "description": "悟性属性，影响经验获取"
    },
    "iDex": {
        "label": "身法",
        "type": int,
        "category": "属性",
        "description": "敏捷属性，影响闪避"
    },
    "iCon": {
        "label": "根骨",
        "type": int,
        "category": "属性",
        "description": "体质属性，影响气血"
    },
    "iAttack": {
        "label": "攻击力",
        "type": int,
        "category": "战斗",
        "description": "基础攻击力"
    },
    "iDefense": {
        "label": "防御力",
        "type": int,
        "category": "战斗",
        "description": "基础防御力"
    },
}

# 可以加到角色 json 对象中的额外字段
EXTRA_ROLE_FIELDS = {
    "iDodge": {"label": "闪避", "type": int},
    "iCrit": {"label": "暴击", "type": int},
    "iCounterAttack": {"label": "反击", "type": int},
}


class SaveEditor:
    """存档编辑器——读取、修改、写回游戏存档。"""

    def __init__(self):
        self.save_dir: Optional[str] = None
        self.save_data: Dict[str, Any] = {}
        self.current_save_path: Optional[str] = None
        self._backup_path: Optional[str] = None

    # ── 存档路径管理 ──────────────────────────────────────────────────

    def find_save_dir(self) -> Optional[str]:
        """自动查找游戏存档目录。"""
        from config import SAVE_DIR_CANDIDATES

        for path in SAVE_DIR_CANDIDATES:
            expanded = os.path.expandvars(path)
            if os.path.isdir(expanded):
                self.save_dir = expanded
                logger.info(f"找到存档目录: {expanded}")
                return expanded

        logger.warning("未找到存档目录，请手动指定")
        return None

    def set_save_dir(self, path: str):
        """手动设置存档目录。"""
        if os.path.isdir(path):
            self.save_dir = path
            logger.info(f"存档目录设为: {path}")
        else:
            raise FileNotFoundError(f"目录不存在: {path}")

    def list_saves(self) -> List[Dict[str, Any]]:
        """列出所有存档文件。"""
        if not self.save_dir:
            self.find_save_dir()
        if not self.save_dir:
            return []

        saves = []
        pattern = os.path.join(self.save_dir, "Save*.Save*")
        for fpath in sorted(glob.glob(pattern)):
            fname = os.path.basename(fpath)
            mtime = os.path.getmtime(fpath)
            size = os.path.getsize(fpath)
            saves.append({
                "path": fpath,
                "name": fname,
                "mtime": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "size": f"{size / 1024:.1f} KB",
            })
        return saves

    # ── 读写存档 ──────────────────────────────────────────────────────

    def load_save(self, filepath: str) -> bool:
        """加载存档文件。"""
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                self.save_data = json.load(f)
            self.current_save_path = filepath
            logger.info(f"已加载存档: {filepath}")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"存档 JSON 解析失败: {e}")
            return False
        except Exception as e:
            logger.error(f"读取存档失败: {e}")
            return False

    def save(self, filepath: str = None) -> bool:
        """写回存档文件，自动创建备份。"""
        target = filepath or self.current_save_path
        if not target:
            logger.error("未指定存档路径")
            return False

        # 创建备份
        try:
            backup = target + ".bak"
            shutil.copy2(target, backup)
            self._backup_path = backup
            logger.info(f"已创建备份: {backup}")
        except Exception as e:
            logger.warning(f"备份创建失败: {e}")

        try:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(self.save_data, f, ensure_ascii=False, indent=2)
            logger.info(f"存档已保存: {target}")
            return True
        except Exception as e:
            logger.error(f"保存存档失败: {e}")
            return False

    def restore_backup(self) -> bool:
        """从备份恢复存档。"""
        if self._backup_path and os.path.exists(self._backup_path):
            shutil.copy2(self._backup_path, self.current_save_path)
            logger.info("已从备份恢复")
            return True
        return False

    # ── 值读取/修改 ──────────────────────────────────────────────────

    def get_value(self, field_path: str) -> Any:
        """
        按路径读取值，路径用点号分隔。

        示例:
            "m_iMoney"         -> 顶层字段
            "RoleData.0.iStr"  -> RoleData 数组第 1 个角色的臂力
        """
        parts = field_path.split(".")
        data = self.save_data
        for part in parts:
            if isinstance(data, dict):
                if part not in data:
                    return None
                data = data[part]
            elif isinstance(data, list):
                try:
                    idx = int(part)
                    data = data[idx]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return data

    def set_value(self, field_path: str, value: Any) -> bool:
        """按路径设置值。"""
        parts = field_path.split(".")
        data = self.save_data
        for part in parts[:-1]:
            if isinstance(data, dict):
                if part not in data:
                    # 自动创建中间字典
                    data[part] = {}
                data = data[part]
            elif isinstance(data, list):
                try:
                    idx = int(part)
                    data = data[idx]
                except (ValueError, IndexError):
                    return False
            else:
                return False

        last_key = parts[-1]
        if isinstance(data, dict):
            data[last_key] = value
            return True
        elif isinstance(data, list):
            try:
                idx = int(last_key)
                data[idx] = value
                return True
            except (ValueError, IndexError):
                return False
        return False

    # ── 快速修改工具 ──────────────────────────────────────────────────

    def set_money(self, amount: int) -> bool:
        """修改金钱。"""
        return self.set_value("m_iMoney", amount)

    def set_attribute_points(self, points: int) -> bool:
        """修改阅历。"""
        return self.set_value("m_iAttributePoints", points)

    def edit_roles(self, role_index: int = None,
                   field_updates: Dict[str, Any] = None) -> bool:
        """
        修改角色数据。

        Args:
            role_index: 角色索引（None 表示所有角色）
            field_updates: 要修改的字段字典，如 {"iStr": 999, "iMaxHp": 9999}

        Returns:
            是否成功
        """
        role_data = self.save_data.get("RoleData", [])
        if not role_data:
            logger.warning("存档中没有角色数据 (RoleData)")
            return False

        if role_index is not None:
            targets = [role_data[role_index]] if role_index < len(role_data) else []
        else:
            targets = role_data

        for role in targets:
            if isinstance(role, dict):
                for field, value in (field_updates or {}).items():
                    role[field] = value

        return True

    def get_roles_info(self) -> List[Dict[str, Any]]:
        """获取角色信息摘要列表。"""
        role_data = self.save_data.get("RoleData", [])
        roles = []
        for idx, role in enumerate(role_data):
            if isinstance(role, dict):
                roles.append({
                    "index": idx,
                    "name": role.get("sName", f"角色{idx}"),
                    "level": role.get("iLevel", 0),
                    "hp": f"{role.get('iHp', 0)}/{role.get('iMaxHp', 0)}",
                    "mp": f"{role.get('iSp', 0)}/{role.get('iMaxSp', 0)}",
                    "str": role.get("iStr", 0),
                    "int": role.get("iInt", 0),
                    "dex": role.get("iDex", 0),
                    "con": role.get("iCon", 0),
                    "attack": role.get("iAttack", 0),
                    "defense": role.get("iDefense", 0),
                })
        return roles

    def max_roles_stats(self):
        """将所有角色属性最大化。"""
        return self.edit_roles(field_updates={
            "iStr": 999,
            "iInt": 999,
            "iDex": 999,
            "iCon": 999,
            "iMaxHp": 99999,
            "iHp": 99999,
            "iMaxSp": 99999,
            "iSp": 99999,
            "iAttack": 9999,
            "iDefense": 9999,
            "iDodge": 999,
            "iCrit": 999,
            "iCounterAttack": 999,
        })

    # ── 存档数据分析 ──────────────────────────────────────────────────

    def dump_structure(self, obj=None, prefix="", depth=0, max_depth=3) -> List[str]:
        """递归打印存档数据结构。"""
        if obj is None:
            obj = self.save_data
        lines = []
        indent = "  " * depth

        if depth > max_depth:
            return [f"{indent}{prefix} ..."]

        if isinstance(obj, dict):
            for key, val in obj.items():
                if isinstance(val, (dict, list)) and val:
                    lines.append(f"{indent}{prefix}{key}:")
                    lines.extend(self.dump_structure(val, "", depth + 1, max_depth))
                else:
                    vtype = type(val).__name__
                    preview = str(val)[:60]
                    lines.append(f"{indent}{prefix}{key} ({vtype}): {preview}")
        elif isinstance(obj, list):
            lines.append(f"{indent}{prefix}[{len(obj)} items]")
            if obj and depth < max_depth:
                for i, item in enumerate(obj[:3]):
                    lines.extend(
                        self.dump_structure(item, f"[{i}] ", depth + 1, max_depth)
                    )
                if len(obj) > 3:
                    lines.append(f"{indent}  ... ({len(obj) - 3} more)")
        else:
            vtype = type(obj).__name__
            lines.append(f"{indent}{prefix} ({vtype}): {str(obj)[:60]}")

        return lines
