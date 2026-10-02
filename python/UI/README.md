# Robocap Decryptor

Desktop GUI for importing user-provided RSA key pairs into the Robocap SDK vault and decrypting folders of MP4 files with the SDK's upstream `python/scripts/bulk_decrypt.py` workflow. The application packages the SDK and FFmpeg tools. It never includes user keys.

## Install

Download the platform artifact from the **Build Robocap Decryptor** GitHub Actions run:

- **macOS:** open `RobocapDecryptor.dmg`, drag the app to Applications, then open it. Builds are provided separately for Intel (`x86_64`) and Apple Silicon (`arm64`). Unsigned builds may require Control-click → Open on first launch.
- **Windows:** download and run `RobocapDecryptor.exe`. Windows SmartScreen may show a warning because the build is not code-signed.

The CI builds are unsigned and unnotarized. macOS users may need to approve the app in Privacy & Security. Signing and notarization require maintainer-owned Apple certificates and credentials.

## Prepare your keys

Keep each device's matching public and private PEM files together in a folder. Names must follow the SDK convention, for example `DEVICE_v1_public.pem` and `DEVICE_v1_private_key.pem`; multiple devices and versions are supported. Select that folder in the GUI and click **Import Keys**.

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

Run these commands in **PowerShell on Windows** from the repository root. Install FFmpeg for the build machine first and make sure both `ffmpeg.exe` and `ffprobe.exe` are on `PATH`; they are bundled into the app, so end users do not need FFmpeg.

```powershell
cd python\UI
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean RobocapDecryptor.spec
```

The Windows executable is `python\UI\dist\RobocapDecryptor.exe`. Windows builds must run on Windows; a Mac build does not produce a Windows executable.

## Build Windows and macOS with GitHub Actions

After pushing the branch, open **Actions → Build Robocap Decryptor → Run workflow**, choose the branch, and start the run. You can also push a tag named `ui-v*` (for example `ui-v1.0.0`) to start it automatically. The workflow builds macOS Intel, macOS Apple Silicon, and Windows x64 on native runners. Download the corresponding workflow artifact from the completed run. It contains `RobocapDecryptor.exe` for Windows or `RobocapDecryptor.dmg` for macOS; local build outputs are under `python/UI/dist/`.

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

Both packaged applications include the SDK, FFmpeg, and ffprobe. End users do not need Python or development tools. Keep the matching public and private PEM files together in the selected key folder; private keys are never bundled with the application.

## Troubleshooting

Application logs are written to `~/.robocap_decryptor/logs/`. The resumable bulk script's completion record is stored as `.robocap-decrypt-done.txt` in the selected output folder. Neither contains key material.
