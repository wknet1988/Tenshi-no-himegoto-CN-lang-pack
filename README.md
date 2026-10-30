# 天使のひめごと — 简体中文汉化工程

**Tenshi no Himegoto — Simplified Chinese Translation Project**

《天使のひめごと》（Nexton / LC-ScriptEngine 引擎，2005）的非官方简体中文汉化源码工程。
本仓库包含全部汉化译文、构建工具链与打包脚本；按原版游戏数据包的 **Shift-JIS (cp932) 直出** 方案实现「零运行时补丁」。

> ⚠️ **法律声明 / Disclaimer**
> 本工程为非官方同人汉化，**不附带任何原版游戏文件**，也不包含受版权保护的数据包二进制。
> 使用本工程构建出的补丁 **仅可用于你已经合法拥有的原版游戏副本**，不得将补丁与原版游戏一并再分发。
> 译文文本版权归译者所有，仅供个人学习、研究使用；本工程与 Nexton 无任何关联。

---

## 汉化范围（v1.0，2026-10-19 全剧情文本完成版）

| 区块 | 内容 |
| --- | --- |
| 序章 | OP001 / OP002 / OP003 / OP004 / OP005A / OP005B / OP006 / INIT |
| 共通线 | CM001 – CM028（全 28 章） |
| 綾线 | AY001 – AY019（全 19 章，AY008 整章不译，见下） |
| 摩菜线 | MA001 – MA019（全 19 章） |
| 结局 / 支线 | ED003 / ED004、退廃线 EL001–EL004 / EL006–EL009、EX001–EX003 |
| H 场景 | 44 个脚本中 34 个摘译了「性戏之后的余韵与剧情段」，共 561 条 |
| UI | 系统文本、存档/读档/回标题/退出确认框、选择枝选项（34/34 全部翻译） |

**合计：注入文本 12,092 条 / 已汉化脚本 123 个。**

### 有意保留日文的部分

以下内容属成人向场景中的露骨性描写，按本项目一贯标准一律保留日文原文，不做翻译；剧情在此处仍可正常推进：

- **整章不译**：ED001（退廃ＥＮＤ）、ED002（姉妹ＥＮＤ）、AY008（綾线０７）、EL005（退廃０６）
- **H 系列 44 个脚本**：34 个只译「性戏之后的剧情段」，性描写部分保留日文；其余 10 个（H008B / H010 / H015 / H016 / H017 / H019 / H021 / H022 / H034 / H035）为整段性描写或仅有碎裂台词，无独立可译剧情，全部保留日文
- MA001 / MA005 / MA006 / MA007 / MA010 / MA011 / MA018 等中的性描写段，均保留日文

因此游戏中会出现「剧情段中文、性场面日文」的交替，这是刻意的处理方式。

### 未汉化：标题画面菜单

标题画面的「はじめから / つぎから / CG viewing / おまけ」等是位图图片资源（`_Title_Chip` 等），不是文本，需重绘图片才能汉化，本工程未处理，仍为日文。

---

## 技术说明（零运行时补丁）

- 数据包内脚本文本以 **Shift-JIS (cp932)** 编码写入，引擎本身即以 cp932 解码；
  无需修改 exe、无需改代码页、无需字体替换、无需任何补丁器。
- 简体字先经字形映射，转换为 cp932 字库可显示的繁体或日文新/旧字体字形
  （例如 这→這、脸→臉、疲惫→疲憊），以便在不改字库的前提下让中文正常显示。
  映射表见 `.work/glyph_map.json`，规则见 `.work/build_glyph_map.py` / `.work/curate_glyph_fallback.py`。
- 数据包结构（文件数 1135、记录索引）与原版一致，未增删任何资源。

---

## 仓库结构

```
.
├── tools/                  # 解包 / 字形映射 / 注入打包 / 分发 工具链
│   ├── lcse_tool.py        # 解包原版、解析 lst、XOR 解密
│   ├── to_jp.py            # 简体 → cp932 可编码字形映射（--apply）
│   ├── build_zh.py         # inject（译文注入 extract）+ repack_all（重打包）
│   └── dist.py             # 生成 汉化补丁/ 补丁包与工具链包
├── .work/
│   ├── zh_backup/          # ★ 译文真源：123 个脚本的简体中文 JSON
│   ├── *_translate.py      # 各脚本的翻译稿与跳过区间定义
│   ├── *_work.txt          # 翻译过程的中间稿 / 决策记录
│   ├── glyph_map.json      # 字形映射表（繁体优先，禁用形近兜底）
│   ├── build_glyph_map.py  # 重建映射表（需外网：zhconv + opencc）
│   ├── curate_glyph_fallback.py  # 人工近义替换修正
│   ├── _deploy_generic.py  # 通用部署：从 zh_backup 全量重建 cn/
│   ├── cm_progress.txt     # 逐脚本进度日志
│   └── README.txt          # 补丁安装说明（随包分发）
├── .workbuddy/memory/      # 项目长期笔记与每日工作日志
├── launch_cn.py            # 启动器（仅改窗口标题为「天使秘事」）
├── run_cn.bat              # 双击启动
├── LICENSE                 # MIT（工具链）
└── NOTICE                  # 同人汉化免责声明
```

> 注：`.work/zh_backup/` 是译文的唯一真源；构建时由 `_deploy_generic.py` 复制为 `.work/zh/`
> 并经 `to_jp.py` 映射后注入。`.work/extract`、`.work/zh`、`.work/build`、`cn/`、`tenshi/`
> 均为构建产物或用户自备输入，不纳入版本库（见 `.gitignore`）。

---

## 从源码构建补丁

### 前置条件

- Python 3.8+（构建工具链仅用标准库；`build_glyph_map.py` 可选，需 `zhconv` + `opencc`）
- 你自己的原版游戏目录，至少包含 `lcsebody`、`lcsebody.lst`（以及 `lcsebody.exe` 用于运行）

### 构建步骤

```bash
# 1) 把原版游戏数据放到 tenshi/（与仓库同级）
#    tenshi/lcsebody  tenshi/lcsebody.lst  tenshi/lcsebody.exe ...

# 2) 从全部译文重建汉化数据包（会重解包原版、映射字形、注入、重打包、部署到 cn/）
python .work/_deploy_generic.py OP001
#    ↑ 脚本名仅用于校验该章；整包会从 zh_backup 全量重建

# 3) 打包为可分发的补丁 zip
python tools/dist.py
#    产物：汉化补丁/天使のひめごと-汉化补丁.zip
```

透明版流水线（等价，逐步可见）：

```bash
python tools/lcse_tool.py extract tenshi .work/extract
python -c "import shutil,os; [shutil.copy('.work/zh_backup/'+f, '.work/zh/'+f) for f in os.listdir('.work/zh_backup') if f.endswith('.json')]"
python tools/to_jp.py --apply
python tools/build_zh.py
python tools/dist.py
```

---

## 应用补丁（给最终玩家）

把补丁里的两个文件放进游戏目录（与 `lcsebody.exe` 同级），覆盖原文件：

```
lcsebody        ← 数据包（脚本、图片、音效索引）
lcsebody.lst    ← 文件索引
```

覆盖前请先备份原版这两个文件。覆盖后直接运行原版 `lcsebody.exe` 即可，
不需要转区、不需要 AppLocale、不需要替换字体、不需要任何补丁器。

### 兼容性

游戏使用旧版 DirectInput，在 Windows 10/11 上可能需：
- 以管理员身份运行，或
- 将兼容性设置为 Windows 7 / XP

若启动时报 DirectInput 错误或约 30 秒后崩溃，属原版在现代 Windows 上的兼容问题（原版同样如此），与汉化无关。

补丁内含 `文件校验.txt`（MD5 / SHA-256），可用于确认下载完整、覆盖成功。

---

## 许可证

- 工具链（Python 脚本）以 **MIT 许可证** 发布，见 `LICENSE`。
- 译文文本归译者所有，以同人汉化用途提供，见 `NOTICE`。

---

## 进度与后续

- v1.0 已完成全部非 H 剧情 + UI 文本 + H 系列余韵段摘译（累计 12,092 条注入）。
- 后续可选项：标题菜单位图重绘汉化、AY008 / ED001 / ED002 / EL005 等整章（按标准暂不译）。
- 详细进度见 `.work/cm_progress.txt` 与 `.workbuddy/memory/`。
