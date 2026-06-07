# Tunneld Diagnosis - 2026-06-07

Project path:

```text
/home/alex/文件/iphone-location-simulator
```

## Finding

The iPhone is visible over USB, so cable/trust/usbmux basic detection is working.

Verified command:

```bash
cd ~/文件/iphone-location-simulator
source .venv/bin/activate
pymobiledevice3 usbmux list
```

Detected device:

```text
DeviceName: Alex chen
ProductType: iPhone14,5
ProductVersion: 26.6
ConnectionType: USB
UDID: 00008110-000539A911DB801E
```

The current blocker is `remote tunneld` permissions:

```text
pymobiledevice3 remote tunneld
ERROR This command requires root privileges. Consider retrying with "sudo".
```

`usbmuxd` is already installed and running. `/dev/net/tun` exists.

## Manual Fix

Start tunneld manually in a Desktop terminal with sudo:

```bash
cd ~/文件/iphone-location-simulator
source .venv/bin/activate
sudo .venv/bin/pymobiledevice3 remote tunneld --host 127.0.0.1 --port 49151 --protocol tcp
```

Leave that terminal open. In another terminal, run the GUI normally:

```bash
cd ~/文件/iphone-location-simulator
source .venv/bin/activate
python src/main.py
```

Then click Connect in the GUI.

## Why

The GUI currently starts tunneld as the normal `alex` user. On Linux, `pymobiledevice3 remote tunneld` needs root privileges for tunnel/network setup, so it times out and the GUI cannot reach `http://127.0.0.1:49151/`.

## Notes

- `sudo -n true` fails because sudo requires a password, so the agent cannot start tunneld automatically.
- `pkexec` exists, but launching it through SSH may not show a usable password prompt on the Desktop session.
