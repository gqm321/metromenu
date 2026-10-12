# Win10 Start Menu for Xfce

一个在 Xfce 桌面上运行的、仿 Windows 10 的经典开始菜单：左侧应用列表，右侧
Metro 磁贴，无边框窗口，支持搜索、磁贴缩放/换色/分组、实时磁贴和电源操作。

实现基于 **PyGObject + GTK3**（原生 GTK 渲染，非 Web 栈），应用发现与启动逻辑
参考了 [xfce4-whiskermenu-plugin](https://gitlab.xfce.org/panel-plugins/xfce4-whiskermenu-plugin)
的做法（freedesktop `.desktop` 解析、XDG 目录去重、`%` 字段码展开、终端启动）。

## 特性

- **两栏布局**：左栏为应用列表 / 搜索，右栏为分组磁贴，左下角固定“设置 / 用户 /
  电源”按钮（设置按钮在用户按钮上方，打开系统设置）。
- **Metro 磁贴**：`small / medium / wide / large` 四种尺寸，任意配色，右键可
  调整大小、更改颜色、移动分组、取消固定。
- **实时磁贴**：`@clock` 时钟、`@date` 日期、`@system` CPU/内存占用，每秒刷新。
- **应用列表**：默认显示“常用”，可切换到“所有应用”（按首字母分组），
  条目右键支持打开、固定到开始屏幕、执行 Desktop Actions。
- **搜索**：按名称 / GenericName / 注释 / 关键词 / 可执行文件加权排序，同时过滤
  左侧列表与右侧磁贴。
- **原生集成**：可从面板 Launcher 按钮启动，也可编译为**原生面板插件**
  （等同 Whisker，出现在“添加新项目”里），还可绑定键盘快捷键（如 `Super`）唤醒。
- **无边框窗口**：`decorated=False`，锚定屏幕工作区左下角，点击外部自动关闭，
  再次触发则切换显示/隐藏。
- **可配置**：布局保存在 `~/.config/win10startmenu/config.json`（纯 JSON）。

## 进程生命周期与开销

菜单是单实例 `Gtk.Application`。默认 `"keep_alive": false`：点击外部 / `Esc` /
启动应用后窗口隐藏，**进程随即退出**（空闲占用为 0）。下次打开需要冷启动。

若希望像 Whisker 那样常驻（再次触发瞬间切换、不重新扫描），把配置改成
`"keep_alive": true`。代价是常驻一个 Python + GTK 进程，实测 RSS 约 **84 MB**
（Whisker 是 C 面板插件，菜单窗口寄居在 `xfce4-panel` 进程内，不额外起进程，
通常十几 MB）。

| 模式 | 空闲内存 | 打开延迟（缓存热） |
| --- | --- | --- |
| `keep_alive: false`（默认） | ~0 | 首帧 ~0.39s，内容 ~0.44s |
| `keep_alive: true` | ~84 MB | 瞬时 |

### 冷启动优化（参考 Whisker 的做法）

Whisker 之所以“秒开”，是因为它常驻面板进程、在**后台线程**里加载菜单并缓存结果。
我们无法常驻（Python+GTK 冷启动约 190ms 不可避免），于是采用等价思路：

1. **先显示后填充**：窗口先 map/绘制（只剩竖栏与搜索框），应用列表与磁贴随后在
   `GLib.idle_add` 里填充 —— 首帧 ~0.39s，内容再花 ~50ms 出现。
2. **应用列表落盘缓存**：解析结果缓存在 `~/.cache/win10startmenu/apps.json`。
3. **图标落盘缓存**：渲染后的图标 PNG 缓存在 `~/.cache/win10startmenu/icons/`
   （20 个图标从 ~100ms 降到 ~5ms）。

**缓存如何失效（安装新软件会自动重扫）**：缓存里存有一份 `.desktop` 文件的指纹
——对每个文件记录 `路径 + mtime + 大小` 后取 SHA1。**安装、卸载或原地修改**任何
`.desktop` 都会改变指纹，下次打开菜单即触发重新扫描（仅 stat 文件，不解析，实测
~10ms）。此外还带 7 天 TTL 兜底。想强制重扫可用 `win10startmenu --no-cache`。



## 目录结构

```
win10startmenu/
├── win10startmenu/          # Python 包
│   ├── application.py       # Gtk.Application / 单实例切换
│   ├── window.py            # 无边框开始菜单窗口与交互
│   ├── apps.py              # freedesktop 应用发现、搜索、启动
│   ├── tiles.py             # Metro 磁贴控件与网格排布
│   ├── icons.py             # 图标加载与缓存
│   ├── config.py            # 配置读写与默认磁贴
│   └── style.css            # Metro 主题
├── assets/                  # 图标（SVG + 多尺寸 PNG）
├── data/                    # .desktop 模板
├── bin/win10startmenu       # 源码树内可直接运行的启动器
├── panel-plugin/            # 原生 Xfce 面板插件（C 源码 + 描述文件）
├── scripts/                 # 安装 / 卸载 / 面板集成 / 快捷键
└── reference/whiskermenu/   # 参考用的 whisker 源码（git clone）
```

## 依赖

- Python 3 与 PyGObject（`python3-gi`）
- GTK 3 运行时、`gir1.2-gtk-3.0`
- 可选：`xfconf`、`xfce4-panel`（用于集成），`systemctl` / `loginctl`（电源操作）

Debian/Ubuntu：

```bash
sudo apt install python3-gi gir1.2-gtk-3.0
```

## 直接运行（源码树）

```bash
./bin/win10startmenu
```

## 安装到用户目录

```bash
./scripts/install.sh              # 安装命令 + 桌面项 + 图标
./scripts/install.sh --panel      # 额外在面板最左侧添加开始按钮
./scripts/install.sh --hotkey     # 额外绑定 <Super> 键
./scripts/install.sh --panel --hotkey='<Super>s'
```

安装脚本会写入：

- `~/.local/share/win10startmenu/`（程序）
- `~/.local/bin/win10startmenu`（命令包装器）
- `~/.local/share/applications/win10startmenu.desktop`
- `~/.local/share/icons/hicolor/*/apps/win10startmenu.png|svg`

## 面板集成原理

Xfce 4.20 支持**用户级**面板插件：描述文件放在
`~/.local/share/xfce4/panel/plugins/`，模块 `.so` 放在
`~/.local/lib/<multiarch>/xfce4/panel/plugins/`（见面板源码
`panel-module-factory.c`，它会从 `XDG_DATA_DIRS`/用户数据目录推导路径）。
插件本质是导出 `xfce_panel_module_construct` 的 `.so`，由面板加载。

### 方式一：原生插件（推荐，等同 Whisker）

```bash
# 一次性安装开发头文件
sudo apt install libgtk-3-dev libxfce4panel-2.0-dev

./scripts/install-panel-plugin.sh          # 编译并安装（用户级，无需 root）
./scripts/install-panel-plugin.sh --add    # 顺便插入 panel-1 最左侧并重启面板
```

`panel-plugin/win10startmenu-plugin.c` 是一个约 120 行的 C 插件：面板按钮点击时，
若已有实例则通过 D-Bus（`org.gtk.Application.Activate`）让其切换，否则启动
`win10startmenu --anchor=x,y,w,h`，把菜单锚定到按钮旁边（面板在下→弹在按钮上方）。
装好后它也会出现在面板的 *添加新项目* 列表里。

### 方式二：Launcher 按钮（无需编译）

Xfce 面板的 Launcher 插件把每个按钮存成
`~/.config/xfce4/panel/launcher-<插件ID>/*.desktop`，并在 xfconf 里登记：

```
/plugins/plugin-<N>        = "launcher"
/plugins/plugin-<N>/items  = [item.desktop]
/panels/panel-1/plugin-ids = [<N>, 7, 2, ...]
```

`scripts/integrate-panel.sh` 会找到空闲插件 ID `N`，创建 `launcher-N/` 目录并写入
一个 `Exec=win10startmenu` 的桌面项，注册 `plugin-N` 并插到 plugin-ids 最前面，
最后 `xfce4-panel --restart`。

因为程序是单实例 `Gtk.Application`，再次点击按钮会切换显示/隐藏。

卸载：

```bash
./scripts/uninstall.sh --panel --hotkey --purge
```

## 快捷键

```bash
./scripts/menu-hotkey.sh '<Super>'      # Windows 键
./scripts/menu-hotkey.sh '<Super>s'
```

若 `Super` 无响应，请在 *设置 → 键盘 → 应用程序快捷键* 中确认它没有被
xfwm4 或 Whisker 菜单占用。

## 配置示例

`~/.config/win10startmenu/config.json`：

```json
{
  "width": 680,
  "height": 672,
  "left_width": 312,
  "opacity": 0.96,
  "keep_alive": false,
  "groups": ["效率", "媒体与娱乐", "实用工具"],
  "tiles": [
    {"id": "@clock",  "size": "medium", "group": "效率", "color": "#0078d7"},
    {"id": "firefox-esr.desktop", "size": "wide", "group": "效率", "color": "#2d7d9a"}
  ]
}
```

删除该文件即可恢复默认布局；`"@clock"` / `"@date"` / `"@system"` / `"@recent"`
为内置特殊磁贴。

## 许可证

GPL-2.0-or-later（与参考的 Whisker Menu 保持一致）。
