# SaveSync

用 Ludusavi 找游戏存档，用 Syncthing 在多台 Windows 游戏设备之间同步，由一台常开的服务器负责中转。

> 程序的界面和提示都是英文的，本文档用中文说明。
>
> 文中的例子用三台设备说明：台式机 **PC**、掌机 **Claw**、常开服务器 **NAS**。换成你自己的设备即可。第一次使用请先看“二、前置要求”和“三、首次安装步骤”。

---

## 一、整个系统怎么运作

### 四个角色

| 角色 | 负责什么 | 什么时候工作 |
|---|---|---|
| **Ludusavi** | 找出每个游戏的存档在哪 | 只在 gamesync 扫描时被调用 |
| **Syncthing**（PC、Claw、NAS 上各一个） | 实际搬运存档文件，双向同步 | 一直在后台 |
| **NAS（beeme）** | 永远开着的中转站，保管最新存档 | 一直在后台 |
| **gamesync** | 把存档路径配置进三台机器的 Syncthing | 只在你运行它的时候 |

**gamesync 只在“建立共享”那一刻起作用，平时同步存档的全是 Syncthing。** 它代替的是你以前手动做的事：打开 Ludusavi 复制路径，再贴进 Syncthing。

### 以 Hades II 为例

**1. 在 PC 上运行 `share`**
- 调用 Ludusavi 扫描，找到存档目录 `C:\Users\ramray\Saved Games\Hades II`。
- 去掉 Steam 游戏，列出其余的。你选 Hades II，再选设备 clawEX。
- 脚本自动完成：
  - 在 **NAS** 上建共享 `gs-hades-ii`，设成同步给 PC 和 Claw；
  - 在 **PC** 上建同一个共享，路径是 PC 上的存档目录；
  - 在 **登记表** 里留一张纸条：“Hades II 放在 `<home>\Saved Games\Hades II`，要给 Claw”。

**2. Claw 开机后运行 `accept`**
- 读登记表里的纸条，把 `<home>` 换成 Claw 自己的用户目录。
- 用这个路径在 Claw 的 Syncthing 里接受共享，然后从 NAS 拉下最新存档。

**3. 之后全自动，gamesync 不用再管**
- 在 PC 上玩，存档变了：推给 NAS。Claw 开着的话，也直接推给 Claw。
- 关掉 PC、打开 Claw：Claw 从 NAS 拿到最新存档。
- 在 Claw 上玩完：推回 NAS，PC 下次开机再拿。

每个游戏只需要 share 一次、accept 一次。反过来也一样：先在 Claw 上玩的游戏，就在 Claw 上 share，到 PC 上 accept。

### 登记表（gamesync-registry）是什么

它是一个**传纸条用的文件夹**，只放说明，不放存档。它本身也是一个 Syncthing 共享，三台机器内容一样：

- PC：`%APPDATA%\gamesync\registry`
- Claw：`%APPDATA%\gamesync\registry`
- NAS：`/srv/media/game/sync/gamesync-registry`

每共享一个游戏，里面就多一个小文件，比如 `gs-hades-ii.json`，写着游戏名、共享 ID、存档位置（用 `<home>` 代替用户名）、给哪些设备，以及不同步的设置文件。

**为什么需要它**：Syncthing 发给对方的共享邀请只写了“有个文件夹要给你”，没写放在哪。Syncthing 本来就不传路径。accept 就是靠这张纸条，才知道该放到对方电脑的哪个目录。PC 和 Claw 用户名不同也没关系。

> 打个比方：Syncthing 的邀请是快递单，登记表是包裹附带的说明书，accept 就是照着说明书把东西放进对的柜子。

**不要删这个文件夹。** 删了以后 accept 就找不到路径了。已经建好的共享不受影响。

### 为什么要调用 NAS 的 API

NAS 只会把共享同步给它配置里写了的设备。gamesync 建共享时，直接在 NAS 上把共享设成“同步给 PC 和 Claw”。这样两台机器不同时开机，也能通过 NAS 中转。

---

## 二、前置要求

在开始之前，下面每一项都要满足。本文档其余部分把“常开服务器”统称为 **NAS**。

### 1. 一台常开的服务器（必须）
它是整个系统的中转站。游戏设备通常不会同时开机，存档要先传到服务器，另一台设备开机后再从服务器拿。

- **设备**：任何能 7×24 小时开着、并能运行 Syncthing 的机器都行，比如 NAS、家用服务器、树莓派、一直开着的旧电脑。操作系统不限（Linux、Windows、群晖/威联通等）。
- **Syncthing**：已安装并设为开机自启。
- **网页/API 必须能从局域网访问**：Syncthing 默认只监听 `127.0.0.1:8384`，也就是只有服务器自己能访问。要在服务器 Syncthing 网页的“操作 → 设置 → 图形用户界面”里，把“监听地址”改成 `0.0.0.0:8384`。gamesync 要从各台游戏设备直接调用服务器的 API，在服务器上创建共享。
- **设置网页的用户名和密码**：开放到局域网以后，建议在同一页面设置，防止局域网里别人打开。gamesync 用 API Key 访问，不受密码影响。
- **记下 API Key**：同一页面（“操作 → 设置 → 常规”）里的 “API 密钥”，初始化时要用。
- **准备一个存放存档的目录**：比如 `/srv/gamesaves`。Syncthing 的运行用户对这个目录要有写权限。gamesync 默认用 `/srv/media/game/sync`，不一样的话，初始化时用 `--nas-root` 指定。

### 2. 每台游戏设备
- **Windows**：目前只支持 Windows 游戏设备，并且只在 Windows 上测试过。Steam Deck 等 Linux 设备暂不支持。
- **gamesync.exe 或 Python（二选一）**：
  - **用 `gamesync.exe`（推荐）**：不需要装 Python，拷过去就能用。
  - **用 `gamesync.py`**：需要 Python 3.11 或更新的版本，安装时勾选 “Add python.exe to PATH”，装好后在终端里运行 `python --version` 能看到版本号。不需要装任何 pip 包。
- **Syncthing**：已安装并在运行。官方版、SyncTrayzor、SyncthingTray 都可以。
  - gamesync 会自动从 `%LOCALAPPDATA%\Syncthing\config.xml` 读取本机 Syncthing 的地址和 API Key，这是 Syncthing 在 Windows 上的默认位置。
  - 如果你用便携版或者自定义了配置目录，运行 gamesync 时加 `--st-home <配置目录>`。
- **Ludusavi**（发起共享的设备需要）：安装后要能在终端里直接运行 `ludusavi`。如果不在 PATH 里，可以在 `config.json` 的 `"ludusavi"` 一项写上完整路径。
  - 第一次运行时 Ludusavi 会下载游戏数据库，需要联网。
  - 只接收存档（只运行 `accept`）的设备可以不装。

### 3. 设备之间的配对
在 Syncthing 里把设备互相添加好（两边都要加对方的设备 ID，并且显示“已连接”）：

| 配对 | 是否必须 | 原因 |
|---|---|---|
| 每台游戏设备 ↔ 服务器 | **必须** | 存档经服务器中转；`init` 会检查这一项 |
| 游戏设备 ↔ 游戏设备 | **必须** | `share` 选设备时，只列出本机 Syncthing 里已经添加的设备。同时在线时，它们也会直接在局域网里同步，更快 |

- **设备名**：gamesync 用 Syncthing 里的设备名来显示和选择（比如 `--devices MyHandheld`）。建议起一个好认的名字。
- **排除规则**：设备名里带 `deck` 的会被自动排除。可以在 `config.json` 的 `exclude_device_patterns` 里修改。

### 4. 服务器上关闭“自动接受”（必须）
在服务器的 Syncthing 网页里，**逐台编辑每个游戏设备 → “共享”选项卡 → 取消勾选“自动接受”**。

- gamesync 通过 API 直接在服务器上创建共享，完全用不到自动接受。
- 如果开着，取消同步（`unshare`）以后，只要另一台设备在运行 `accept` 之前连上服务器，服务器就会把共享自动建回来。
- 以后每新增一台游戏设备，都要记得关掉它的自动接受。

### 5. 网络
- 每台游戏设备要能访问服务器的 **8384 端口**（API）。最简单的办法是在同一个局域网里；不在家时可以用 Tailscale、ZeroTier 这类 VPN。
- **不建议把 8384 端口直接暴露到公网。**
- Syncthing 自身的同步连接（默认 22000 端口，或者走中继）要能连通。“设备已连接”就说明没问题。

---

## 三、首次安装步骤

按顺序做一次即可。

**第 1 步：服务器**
按上面“前置要求 1”装好 Syncthing，改监听地址、设密码、记下 API Key、准备存档目录。

**第 2 步：每台游戏设备装软件**
装好 Syncthing，发起共享的设备还要装 Ludusavi。用 `gamesync.py` 的话还要装 Python，用 `gamesync.exe` 不用。

**第 3 步：配对**
- 在 Syncthing 里把每台游戏设备和服务器互相添加，游戏设备之间也互相添加。
- 在服务器上把每台游戏设备的“自动接受”关掉。
- 等所有设备都显示“已连接”。

**第 4 步：在每台游戏设备上初始化**
把 `gamesync.exe` 拷到这台设备上（放在哪都行），然后任选一种方式：
- **双击 `gamesync.exe`**，在菜单里选 `6. init`，按提示依次输入：
  - 服务器上的存档目录（直接回车用默认的 `/srv/media/game/sync`）；
  - 服务器地址（如 `http://192.168.1.10:8384`）；
  - 服务器的 API Key。
- **或者在终端里一次写全**：
  ```
  gamesync.exe init --nas-url http://<服务器IP>:8384 --nas-key <服务器的 API Key> --nas-root <服务器上的存档目录>
  ```
  存档目录就是默认的 `/srv/media/game/sync` 的话，可以省略 `--nas-root`。

用 Python 版的话，把上面的 `gamesync.exe` 换成 `python gamesync.py` 即可。

- 看到 `Init complete.` 就成功了。
- `init` 会：保存配置到 `%APPDATA%\gamesync\config.json`；检查本机和服务器是否互相认识；在本机和服务器上建立登记表共享 `gamesync-registry`。
- 可以重复运行，不会重复创建。

**第 5 步：确认**
- 菜单里选 `5. status`：不报错就说明连接正常。
- 菜单里选 `2. preview`：列出可共享的游戏和将要同步的目录，但不创建任何共享。确认结果合理后，再正式选 `1. share`。

---

## 四、使用方法

### 双击打开（最简单）
直接双击 `gamesync.exe`（或者不带参数运行 `python gamesync.py`），会出现菜单：

```
=== gamesync: game save sync ===

  1. share    Share saves: scan with Ludusavi, pick games and devices
  2. preview  Preview what share would sync (changes nothing)
  3. accept   Accept new saves shared to this device; also drops ones already unshared elsewhere
  4. unshare  Stop syncing a save on all devices (files are kept)
  5. status   Show sync status
  6. init     Set up this device (run once per device)
  0. exit
```

- 输入编号回车就能执行，后续的选择（选游戏、选设备等）都会一步步提示。
- 执行完按回车回到菜单，可以接着做别的。
- 输入 `0` 或直接回车退出。

### 命令行（带参数）
也可以直接带命令运行，适合写脚本或者想跳过提示的时候。`gamesync.exe` 和 `python gamesync.py` 用法完全一样：

| 命令 | 作用 | 对应菜单 |
|---|---|---|
| `gamesync.exe share` | 扫描存档 → 选游戏 → 选设备 → 建共享 | 1 |
| `gamesync.exe share --dry-run` | 预览，不创建任何共享 | 2 |
| `gamesync.exe accept` | 接受别的设备发来的新存档共享；如果某个共享已经在别的设备上被 `unshare` 取消了，本机这边也跟着停掉（不会主动取消任何共享） | 3 |
| `gamesync.exe unshare` | 取消某个游戏的同步（所有设备，文件保留） | 4 |
| `gamesync.exe status` | 查看所有存档共享的同步状态 | 5 |
| `gamesync.exe init` | 初始化本机（每台设备一次） | 6 |

### share 的选项
- `--dry-run`：只看列表和要同步的目录，不创建任何共享。第一次用建议先跑一下。
- `--all`：连被排除的游戏也显示，比如 Steam 游戏，并标出排除原因。被排除的游戏也可以选。
- `--devices clawEX`：直接指定目标设备，不再询问。
- `--yes`：不再逐个确认。没有指定下面两个参数时，默认不同步设置文件。
- `--include-config`：设置文件也一起同步，不再询问。
- `--exclude-config`：不同步设置文件，也不再询问。

---

## 五、规则和注意事项

### 哪些游戏会被排除
- **Steam 游戏**：满足下面任一条件就排除（Steam 云存档已经管了）：
  - 在 Steam 里装着；
  - 存档在 Steam 目录里（比如 `steam\userdata`）。
- **只有注册表存档的游戏**：注册表没法用 Syncthing 同步。
- **已经共享过的游戏**：不会重复建共享，但仍然可以选来增加设备。

### 同步哪个目录
- 按 Ludusavi 数据库里的存档路径，选最贴近这个游戏的目录。
- 不会同步整个 `AppData\Local`、`Documents`、`My Games`、`Saved Games` 这类公共目录。
- 一个游戏的存档分散在几个地方时，会建几个共享（比如 Forza Horizon 6 会建两个）。
- 如果和已有的共享互相包含，会跳过并提示。

### 设置文件（分辨率、画质、按键）
PC 和 Claw 的屏幕不一样，画面设置不应该互相覆盖。Ludusavi 的数据库会给每个文件标上“存档”或“设置”，share 时会按这个区分：

- 如果检测到设置文件，会列出来并询问 `Also sync these settings files? [y/N]`。**直接回车就是不同步。**
- 选择不同步时：
  - 只按存档文件决定同步哪个目录。比如 FragPunk 只同步 `Saved\SaveGames`，整个 `Config` 目录不同步。
  - 同步目录里如果还有设置文件，会加进 Syncthing 的忽略列表（`.stignore`）。比如 Hades II 同步整个目录，但不同步 `GlobalSettingsWin.sjson`。
  - 忽略规则会写进登记表，Claw 运行 accept 时自动套用。每台设备保留自己的设置，互不影响。
- 有的游戏只有设置文件，存档在服务器上（比如 Apex Legends、Marathon）。这类游戏会显示 “Only settings files found” 并跳过。
- `share --dry-run` 会列出每个游戏要忽略哪些设置。

限制：
- 把设置和存档写在同一个文件里的游戏，没法拆开。
- 设置文件里通常还有按键、音量、语言，选择不同步时这些也各自保留。
- 标签来自 PCGamingWiki，个别游戏可能标错。没有标签的文件一律当作存档同步，宁可多同步也不会丢进度。

### 已有存档的冲突
如果 Claw 上已经有同一个游戏的存档，接受共享后交给 Syncthing 合并：较新的文件胜出，较旧的一版会改名成 `xxx.sync-conflict-日期-xxx` 留在原处，可以手动删掉。

### 版本备份
NAS 上的每个存档共享都开了版本备份，每个文件保留最近 10 个旧版本，放在 NAS 对应目录下的 `.stversions` 里。存档被误覆盖时可以去那里找回。

### 共享的命名
- 共享 ID：`gs-游戏名`，比如 `gs-hades-ii`。
- 显示名：`Save - 游戏名`。
- NAS 上的位置：`/srv/media/game/sync/gs-游戏名`。

### 不再同步某个游戏（unshare）
1. 在**任意一台**设备上运行 `python gamesync.py unshare`，选择要取消的游戏。
   - 本机和 NAS 上的共享会立刻删掉。
   - 登记表里这条记录会标成“已取消”，而不是直接删除。
2. 另一台设备下次运行 `python gamesync.py accept` 时，会看到这个标记，自动停止同步，并提示 `Stopped syncing ...`。

说明：
- **存档文件一律保留**：各设备上的存档原样留着，游戏还能接着玩；NAS 上的副本也留着，可以当备份，不需要了就手动删。
- 取消后还会让各设备忽略这个共享的邀请，Syncthing 网页上不会一直弹“有设备想共享文件夹”。
- 以后想重新同步同一个游戏，直接再 `share` 一次就行，会分配一个新的 ID（比如 `gs-xxx-2`）。
- 可以用 `--game gs-xxx`（或游戏名）直接指定，不列菜单；`--yes` 跳过确认。

### NAS 上必须关闭“自动接受”
在 NAS 的 Syncthing 里，每台游戏设备的“自动接受”都必须保持**关闭**（见“前置要求 4”）。

gamesync 在 NAS 上建共享都是通过 API 直接完成的，用不到自动接受。如果开着，unshare 以后只要另一台设备在 accept 之前连上 NAS，NAS 就会把共享自动建回来（放在一个以显示名命名的新目录里）。Syncthing 的忽略列表挡不住自动接受。

### Steam Deck
目前不支持，不会出现在设备列表里。

---

## 六、常见问题

**accept 显示 “No save shares waiting to be accepted”，但 Syncthing 里有邀请**
登记表还没同步过来。确认 NAS 在线，等几十秒再运行一次。

**报错 “Cannot reach NAS Syncthing”**
- 检查 NAS 是否开机，以及在这台设备的浏览器里能不能打开 `http://<服务器IP>:8384`。
- 打不开的话，多半是服务器的监听地址还是 `127.0.0.1`（见“前置要求 1”），或者防火墙挡了 8384 端口。

**报错 “The NAS Syncthing does not know this device yet” 或 “has not added the NAS device yet”**
设备没有互相配对，见“前置要求 3”。

**share 选设备时，看不到另一台游戏设备**
本机 Syncthing 里还没添加那台设备（见“前置要求 3”），或者它的名字里带 `deck`，被排除了。

**报错 “Cannot find ludusavi”**
Ludusavi 不在 PATH 里。在 `config.json` 的 `"ludusavi"` 一项写上完整路径，比如 `"C:\\Tools\\ludusavi.exe"`。

**报错 “Cannot find the local Syncthing config.xml”**
本机 Syncthing 的配置不在默认位置，运行时加 `--st-home <配置目录>`。

**双击 gamesync.exe 时 Windows 弹出“已保护你的电脑”（SmartScreen）**
`gamesync.exe` 没有数字签名，第一次运行时 Windows 可能会拦一下。点“更多信息 → 仍要运行”即可。杀毒软件偶尔也会误报 PyInstaller 打包的程序；不放心的话，可以改用 `python gamesync.py`，效果完全一样。

**修改了 gamesync.py 以后，怎么重新生成 exe**
在 `gamesync` 文件夹里运行（需要 Python，先 `pip install pyinstaller`）：
```
pyinstaller --onefile --console --name gamesync --distpath . gamesync.py
```
生成的 `gamesync.exe` 会覆盖旧的。打包过程中产生的 `build\` 文件夹和 `gamesync.spec` 可以删掉。

**报错 “This device is not initialized”**
先运行 `python gamesync.py init`。

**想换 NAS 地址或 Key**
编辑 `%APPDATA%\gamesync\config.json`，或者带新参数重新运行 `init`。

---

## 七、文件清单

| 文件 | 说明 |
|---|---|
| `gamesync.exe` | 打包好的程序，不需要装 Python，双击就能用 |
| `gamesync.py` | 程序源码，只用 Python 自带的库；`gamesync.exe` 就是用它打包的 |
| `test_gamesync.py` | 单元测试，运行 `python -m unittest` |
| `testdata\` | 单元测试用的样本数据 |
| `说明.md` | 本文档 |
| `%APPDATA%\gamesync\config.json` | 配置文件：NAS 地址、API Key 等（每台机器各一份） |
