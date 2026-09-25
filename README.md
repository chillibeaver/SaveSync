# SaveSync

Sync PC game saves across your Windows gaming devices.

SaveSync uses [Ludusavi](https://github.com/mtkennerly/ludusavi) to find each game's save folder and [Syncthing](https://syncthing.net) to sync it. An always-on server relays the saves, so your devices don't need to be on at the same time. Steam games are skipped, since Steam Cloud already covers them.

Share a game once on one device, accept it once on the others, and Syncthing handles the rest.

---

## Requirements

- **An always-on server** running Syncthing: a NAS, home server, Raspberry Pi, or any PC that stays on. Any OS.
- **Windows gaming devices** with Syncthing installed. Linux devices are not yet supported.
- **Ludusavi** on devices that share games. Devices that only receive saves don't need it.
- **Python 3.11+** only if you use `gamesync.py` instead of `gamesync.exe`. No extra packages needed.

---

## Setup

### 1. Server

In the server's Syncthing web GUI, open **Actions → Settings → GUI**:

- Set **GUI Listen Address** to `0.0.0.0:8384`, so your devices can reach the API.
- Set a GUI username and password.
- Copy the **API Key**.

Then create a folder for saves that Syncthing can write to. The default is `/srv/media/game/sync`.

Don't expose port 8384 to the internet. To use SaveSync away from home, use a VPN such as Tailscale or ZeroTier.

### 2. Pair devices

In Syncthing, add every gaming device and the server to each other, and add the gaming devices to each other. Wait until they all show **Connected**.

Then, on the server, edit each gaming device → **Sharing** tab → uncheck **Auto Accept**. Otherwise, unshared games can come back on their own.

Devices are shown by their Syncthing name, so give them clear names. Devices with `deck` in the name are hidden.

### 3. Initialize each gaming device

Double-click `gamesync.exe`, choose `6. init`, and enter the server's save folder, address (e.g. `http://192.168.1.10:8384`), and API key. Or run:

```
gamesync.exe init --nas-url http://<server IP>:8384 --nas-key <API key> --nas-root <save folder>
```

`--nas-root` can be left out if you use the default folder. For the Python version, replace `gamesync.exe` with `python gamesync.py` in all commands.

You're done when you see `Init complete.` Run `5. status` to check the connection, then `2. preview` to see what would be synced.

---

## Usage

Double-click `gamesync.exe` to open the menu, or run the commands directly:

| Command | Menu | What it does |
|---|---|---|
| `share` | 1 | Pick games and devices to sync |
| `share --dry-run` | 2 | Preview only, changes nothing |
| `accept` | 3 | Accept saves shared to this device |
| `unshare` | 4 | Stop syncing a game on all devices (files are kept) |
| `status` | 5 | Show sync status |
| `init` | 6 | Set up this device |

**`share` options**

- `--all`: also show excluded games (e.g. Steam games).
- `--devices <name>`: choose target devices without being asked.
- `--yes`: skip confirmations. Settings files are not synced unless you add `--include-config`.
- `--include-config` / `--exclude-config`: sync or skip settings files without being asked.

**`unshare` options**

- `--game <ID or name>`: choose the game without the list.
- `--yes`: skip confirmation.

---

## Good to know

- **Excluded games:** Steam games, and games that only save to the Windows registry.
- **Settings files:** graphics and control settings are not synced by default, so each device keeps its own. You're asked for each game during `share`.
- **Games with saves in several places** get one synced folder per location.
- **Existing saves:** if a device already has saves for a game, the newest file wins. The older one is kept as `*.sync-conflict-*`.
- **Backups:** the server keeps the last 10 versions of every save file in `.stversions` inside the game's folder.
- **Unshare** keeps all save files. Other devices stop syncing the next time they run `accept`.
- **Don't delete the `gamesync-registry` folder.** `accept` needs it to know where each game's saves go.

---

## Troubleshooting

**`accept` finds nothing, but Syncthing shows an invitation**
Wait a few seconds for the registry to sync from the server, then run `accept` again.

**"Cannot reach NAS Syncthing"**
Open `http://<server IP>:8384` in a browser on this device. If it doesn't load, check the server's GUI Listen Address and firewall.

**"The NAS Syncthing does not know this device yet" / "has not added the NAS device yet"**
The device and the server aren't paired in Syncthing.

**A device is missing from the list in `share`**
It isn't added in this device's Syncthing, or its name contains `deck`.

**"Cannot find ludusavi"**
Set the full path in the `"ludusavi"` entry of `%APPDATA%\gamesync\config.json`, e.g. `"C:\\Tools\\ludusavi.exe"`.

**"Cannot find the local Syncthing config.xml"**
Run gamesync with `--st-home <Syncthing config folder>`.

**Windows SmartScreen blocks gamesync.exe**
The exe is unsigned. Click **More info → Run anyway**, or use `python gamesync.py` instead.

**Changing the server address or API key**
Run `init` again, or edit `%APPDATA%\gamesync\config.json`.
