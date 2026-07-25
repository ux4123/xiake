# Claw's Trainer — 《侠客风云传前传》多功能修改器

> 适用于 Steam / 凤凰游戏 平台的《侠客风云传前传》  
> 进程名: `YoungHero.exe` | 引擎: Unity 3D (Mono) | 架构: 32-bit

---

## ☁️ 云端一键构建（无需 Windows，无需安装任何东西）

**最快的获取方式：** 用 GitHub Actions 在云端自动构建

| 步骤 | 操作 |
|------|------|
| ① | 把 `trainer/` 文件夹上传到你的 GitHub 仓库 |
| ② | 在仓库页面点 **Actions → Build ClawTrainer.exe → Run workflow** |
| ③ | 等 3-5 分钟 |
| ④ | 下载 **Artifacts** 里的 `ClawTrainer.exe` |

> 整个构建在 GitHub 的 Windows 云服务器上自动完成，  
> 你只需要一个浏览器，手机/平板/电脑都可以操作。  
> 构建结果是一个 **单文件 .exe，双击直接运行，无需安装 Python**。

---

## 📥 获取方式对比

| 方式 | 需要什么 | 耗时 | 适合场景 |
|------|---------|------|---------|
| ☁️ **GitHub Actions**（推荐） | GitHub 账号 + 浏览器 | 3-5 分钟 | 没有 Windows 机器 / 不想装环境 |
| 🖥️ **本地 build.bat** | Windows 电脑 + 有网 | 2-5 分钟 | 已有 Windows 电脑 |
| 🐍 **源码运行** | Python 3.7+ | 立即 | 开发者 / 调试 |

---

### 方式 A：☁️ GitHub Actions 云端构建（零本地依赖）

```
1. 在 GitHub 上创建一个新仓库（公开或私有都行）
2. 把 trainer/ 里的所有文件 push 到仓库
   确保 .github/workflows/build.yml 也在仓库里
3. 打开仓库 → 点 Actions 标签页
4. 左侧点 "Build ClawTrainer.exe" → 右侧点 "Run workflow"
5. 等 3-5 分钟刷新页面
6. 点进完成的 workflow run → 在 Artifacts 区域下载 .zip
7. 解压得到 ClawTrainer.exe，双击运行！
```

> 工作流文件位于 `.github/workflows/build.yml`，配置了：
> - `windows-latest` 云构建机
> - Python 3.11 + PyInstaller 打包
> - 自动上传构建产物（保留 30 天）
> - 支持手动触发 或 push 到 main 分支自动触发

### 方式 B：🖥️ 本地 Windows 构建

在 Windows 电脑上：

```cmd
1. 将 trainer/ 文件夹复制到 Windows 电脑
2. 双击 build.bat（自动安装依赖 + 打包）
3. 在 dist/ 目录找到 ClawTrainer.exe
```

### 方式 C：🐍 源码直接运行

```bash
pip install -r requirements.txt
python main.py
```

---

## 🚀 功能列表

| 类别 | 功能 | 方式 |
|------|------|------|
| 💰 **资源修改** | 金钱、阅历、声望 | 内存扫描 / 存档编辑 |
| ⚔️ **战斗辅助** | 无限气血/内力、一击必杀、无限行动、技能无冷却、敌人不能动 | 内存（扫描+锁定） |
| 🔍 **内存扫描** | 数值搜索（i32/f32/i16...）、筛选过滤、地址锁定 | 实时内存 |
| 🔒 **数值冻结** | 后台线程持续写入，任何地址任意值类型 | 后台操作 |
| 💾 **存档编辑** | 全角色属性（臂力/悟性/身法/根骨到 999）、武艺满级、一键最大化 | JSON 存档 |
| 📋 **日志面板** | 实时操作日志输出 | 内置 UI |

---

## 🎯 快速使用

### 内存修改（实时生效）

1. 启动游戏 → 双击 `ClawTrainer.exe`
2. 点击 **「附加进程」**（状态栏显示 `✅ PID=xxxx`）
3. **「内存扫描」** 标签页：
   - 输入游戏中某个值（如金钱 `5000`）
   - 点击 **「首次扫描」**
   - 回游戏花掉一些钱 → 输入新值 → **「再次扫描」**
   - 重复直到只剩 1~2 个地址 → **「锁定选中」**

### 存档修改（永久生效，最稳定）

1. **「存档编辑」** 标签页 → **「查找存档」**
2. 选择存档 → **「全角色属性最大化」**
3. **「保存修改」** → 游戏里**重新读取**存档

---

## 🛠️ 项目文件

```
trainer/
├── .github/
│   └── workflows/
│       └── build.yml          ← ☁️ GitHub Actions 云端构建配置
├── build.bat                   ← 🖥️ Windows 本地一键构建
├── trainer.spec                ← PyInstaller 打包配置
├── main.py                     ← 主界面（tkinter GUI，6 标签页）
├── memory_engine.py            ← 内存操作引擎（pymem 封装）
├── save_editor.py              ← 存档编辑器（JSON 解析）
├── config.py                   ← 游戏参数、热键、存档路径
├── requirements.txt            ← Python 依赖
└── README.md                   ← 本文件
```

构建产物：`dist/ClawTrainer.exe`（25~35 MB 单文件）

---

## ⚙️ 技术细节

### 存档格式
- 位置: `Documents\Heluo\TaleOfWuxiaPre\Config\SaveData\`
- 格式: **JSON 明文**（可记事本直接编辑）
- 关键字段: `m_iMoney`(金钱), `m_iAttributePoints`(阅历), `iMaxHp`/`iHp`(气血), `iMaxSp`/`iSp`(内力), `iStr`/`iInt`/`iDex`/`iCon`(四维属性)

### 内存架构
- Unity 3D (Mono 运行时) | 32-bit 进程 | 使用 `pymem` 库进行跨进程操作

### 打包技术
- **PyInstaller** `--onefile` 模式，全部打包进一个 .exe
- **无控制台窗口**（`console=False`），静默运行
- UPX 压缩，减小体积约 30%
- 排除不必要的模块以减小体积

---

## ⚠️ 安全声明
- **仅限单机游戏使用**
- 修改存档前自动创建 `.bak` 备份文件
- 杀毒软件对内存修改器存在误报，属于正常现象
