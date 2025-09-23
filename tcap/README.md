# Installation with only one command!!

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Kamil-Krawiec/yt/tcap_testing/tcap/install_tcap.sh) --user
```

it installes `tcap` package automatically in `--user` option (only for current user). More on installing options [here](https://github.com/Kamil-Krawiec/yt/blob/161f4b64650f051ce1eead65b2b02b3ff79dac9e/tcap/install_tcap.sh#L42)

# tcap Installer

`tcap` appends a still PNG to the end of an MP4 so you always land on the right
thumbnail frame when scrubbing or uploading clips. This repository ships a
single script—`install_tcap.sh`—that sets up the CLI, Python environment, and
FFmpeg dependencies for you.

## Requirements

- Python 3 with `venv`
- `ffmpeg` + `ffprobe`
- A supported package manager (`apt`, `dnf`, `yum`, `pacman`, `zypper`, `apk`, or `brew`) if you want the script to install missing packages automatically.

If the packages are already installed, run the installer with
`--skip-packages` to skip system package operations.

## Installation

### User install (no sudo)
```bash
./install_tcap.sh
```
Installs to `~/.local/share/tcap` and links the launcher to `~/.local/bin/tcap`.
The installer ensures that directory is added to your `PATH` for future shells.

### System install (requires sudo)
```bash
sudo ./install_tcap.sh --system
```
Installs to `/opt/tcap` with the launcher at `/usr/local/bin/tcap`.

### Useful flags
- `--force` — rebuild the virtualenv and overwrite existing launchers.
- `--prefix DIR` — put the installation files in `DIR` (combine with `--bin-dir`).
- `--bin-dir DIR` — choose where the launcher script lives.
- `--skip-packages` — disable automatic package installation and only verify binaries.

Run `./install_tcap.sh --help` for the full list of options with descriptions.

## Typical usage
Once installed, the CLI is available as `tcap`:
```bash
tcap --pair footage.mp4         # expects footage.png alongside the video
tcap -v clip.mp4 -t still.png   # explicit paths
tcap --pair short.mp4 --inplace # overwrite the original video
tcap --info                     # show version, paths, dependency status
```

Additional tweaks:
- `--duration 0.5` lengthens the appended still.
- `--crf 20` adjusts x264 quality (lower is higher quality/bigger file).
- `--audio-bitrate 256k` sets the AAC bitrate for the appended still.

## Updating or removing
- Re-run the installer with `--force` to update in place.
- Remove any older `tcap` binaries that appear before the new launcher on your
  `PATH` (for example `/usr/local/bin/tcap`).
- Delete the install directory and launcher to remove the tool:
  ```bash
  rm -rf ~/.local/share/tcap ~/.local/bin/tcap
  ```
  Replace the paths with the system locations if you installed with sudo.

# Troubleshooting

After installing i cant see the tcap package:
- try refreshing your terminal with `exec bash -l` (or `exec zsh -l`).

Enjoy faster thumbnail selection!
