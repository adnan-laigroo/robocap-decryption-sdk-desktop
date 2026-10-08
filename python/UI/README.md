# Robocap Decryptor

Desktop GUI for importing user-provided RSA key pairs into the Robocap SDK vault and decrypting folders of MP4 files with the SDK's upstream `python/scripts/bulk_decrypt.py` workflow. The application packages the SDK and FFmpeg tools. It never includes user keys.

## Bulk decrypt quick start

1. Install or open the app for your operating system (steps below).
2. Put each device's matching public and private PEM files together in one key folder.
3. In the app, choose **Keys Folder** and click **Import Keys**.
4. Choose the folder that contains the MP4 files as **Input Folder**.
5. Choose a different **Output Folder** outside the input folder.
6. Set the number of workers and click **Start Decryption**.

Watch the log for progress and the final counts. The input videos stay in place, and decrypted copies go to the output folder. The output folder must not be inside the input folder.

## Install

For a permanent download, open the repository's **Releases** page and download the asset for your platform. Each `ui-v*` tag builds the Windows executable and macOS disk images and attaches them to a GitHub Release. Manual workflow runs also create downloadable Actions artifacts, which expire after 30 days.

- **macOS:** download `RobocapDecryptor-macos-x86_64.dmg` for Intel or `RobocapDecryptor-macos-arm64.dmg` for Apple Silicon. Open the DMG and drag the app to Applications. Because the release is unsigned and unnotarized, macOS may block its first launch. If you trust the official release, try opening it once, then go to **Apple menu → System Settings → Privacy & Security → Open Anyway** and confirm **Open**. You can also Control-click the app and choose **Open**.
- **Windows:** download and run `RobocapDecryptor.exe`. Windows SmartScreen may show a warning because the build is not code-signed.
The CI builds are unsigned and unnotarized. macOS users may need to approve the app in Privacy & Security. Signing and notarization require maintainer-owned Apple certificates and credentials. Windows builds bundle FFmpeg, ffprobe, and the FFmpeg DLLs; end users do not need to install FFmpeg, Python, or the SDK.

## Prepare your keys

Keep each device's matching public and private PEM files together in the selected folder. The GUI accepts either `DEVICE_v1_public.pem` or `DEVICE_v1_public_key.pem` for the public key; the private key should be named `DEVICE_v1_private_key.pem`. The device ID and version must match across each pair, for example `camera123_v1_public_key.pem` with `camera123_v1_private_key.pem`. Multiple devices and versions are supported.

Private keys are not bundled in the app, copied into its resources, or written to application logs. Import reads the selected files and the SDK stores its protected vault copy under `~/.robocap-sdk/vault/` (under your user home directory on Windows). The app stores only folder paths and worker count in `~/.robocap_decryptor/settings.json`.

## Decrypt

1. Select **Keys Folder** and click **Import Keys**.
2. Select **Input Folder**.
3. Select **Output Folder**.
4. Set the worker count.
5. Click **Start Decryption**.

The output folder must be outside the input folder. For example, use `Downloads/output` for input `Downloads/test_bulk`, not `Downloads/test_bulk/output`. The GUI checks this before starting. Progress and script output appear in the application log; decryption runs off the UI thread.

The app runs the repository's real `python/scripts/bulk_decrypt.py`, which uses each MP4's metadata to select the device and SDK key version. It does not try every key against every file. FFmpeg and ffprobe are included in the distributable builds.

## Build locally on macOS

Run these commands from the repository root on the Mac architecture you want to build for. PyInstaller makes a native build; a local Mac build does not create a Windows `.exe`.

```bash
brew install ffmpeg
cd python/UI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean RobocapDecryptor.spec
hdiutil create -volname RobocapDecryptor \
  -srcfolder dist/RobocapDecryptor.app \
  -ov -format UDZO dist/RobocapDecryptor.dmg
```

The `.app` and `.dmg` are under `python/UI/dist/`. Run `python main.py` from `python/UI` for source development.

## Build the Windows `.exe` locally

Run these commands in **PowerShell on Windows** from the repository root. Install FFmpeg for the build machine first. Set `ROBOCAP_FFMPEG_DIR` to the FFmpeg `bin` folder containing `ffmpeg.exe`, `ffprobe.exe`, and the accompanying DLLs so PyInstaller can bundle the complete runtime.

```powershell
cd python\UI
choco install ffmpeg --no-progress -y
$ffmpeg = Get-ChildItem "$env:ChocolateyInstall\lib" -Filter ffmpeg.exe -File -Recurse | Where-Object { Test-Path (Join-Path $_.DirectoryName 'ffprobe.exe') } | Select-Object -First 1
if (-not $ffmpeg) { throw 'Could not find the FFmpeg bin folder containing ffmpeg.exe and ffprobe.exe.' }
$env:ROBOCAP_FFMPEG_DIR = $ffmpeg.DirectoryName
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean RobocapDecryptor.spec
```

The Windows executable is `python\UI\dist\RobocapDecryptor.exe`. Windows builds must run on Windows; a Mac build does not produce a Windows executable.

## Build Windows and macOS with GitHub Actions

For a temporary build, open **Actions → Build Robocap Decryptor → Run workflow**, choose the branch, and start the run. Download the Windows or macOS artifact from the completed run; Actions artifacts expire after 30 days.

To build and keep the downloads on the repository's **Releases** page, push a version tag from the repository root:

```bash
git tag ui-v1.0.0
git push origin ui-v1.0.0
```

The tag starts builds for macOS Intel, macOS Apple Silicon, and Windows x64 on native runners. After all builds succeed, Actions creates a GitHub Release with `RobocapDecryptor.exe`, `RobocapDecryptor-macos-x86_64.dmg`, and `RobocapDecryptor-macos-arm64.dmg` attached. Use a new tag for each release version. Local build outputs are under `python/UI/dist/`.

## Install and use

### macOS

1. Download the macOS `.dmg` artifact for your processor (`x86_64` for Intel or `arm64` for Apple Silicon).
2. Open the DMG and drag `RobocapDecryptor.app` into Applications.
3. Open the app. Because builds are unsigned and unnotarized, macOS may ask you to approve it in Privacy & Security or open it using Control-click → **Open**.
4. Select your key folder and click **Import Keys**.
5. Choose an input folder and an output folder outside it, set the worker count, and click **Start Decryption**.

### Windows

1. Download the Windows x64 artifact and extract it if your browser saved it as a ZIP.
2. Run `RobocapDecryptor.exe`. Windows SmartScreen may show a warning because the build is not code-signed.
3. Select your key folder and click **Import Keys**.
4. Choose an input folder and an output folder outside it, set the worker count, and click **Start Decryption**.

Both packaged applications include the SDK, FFmpeg, and ffprobe. The Windows app also bundles FFmpeg's adjacent DLLs, so end users do not need to install FFmpeg or any Python development dependencies. Keep the matching public and private PEM files together in the selected key folder; private keys are never bundled with the application.

## Troubleshooting

Application logs are written to `~/.robocap_decryptor/logs/`. The resumable bulk script's completion record is stored as `.robocap-decrypt-done.txt` in the selected output folder. Neither contains key material.

- **A file says “already recorded as done”:** the app skips it because its relative path has a successful entry in the completion record. If you need to retry that file, remove only its line from `.robocap-decrypt-done.txt` in the output folder, then run decryption again.
- **Output validation fails:** the app probes each decrypted output with bundled ffprobe. Current builds also check the video stream when the MP4 container does not report a duration. If ffprobe cannot read a video stream, the GUI log includes its exit code and any diagnostics; the original input remains unchanged.
- **Windows says FFmpeg is missing:** download the current `RobocapDecryptor.exe` from Releases. The executable bundles FFmpeg, ffprobe, and their DLLs, so installing FFmpeg separately should not be necessary.
