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

Run these commands from the repository root:

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

## Build Windows and macOS with GitHub Actions

Push the branch and use **Actions → Build Robocap Decryptor → Run workflow**, or push a tag named `ui-v*` (for example `ui-v1.0.0`). The workflow builds macOS Intel, macOS Apple Silicon, and Windows x64 on native runners. Download the corresponding workflow artifacts. Windows output is `RobocapDecryptor.exe` under `python/UI/dist/`; macOS output is `RobocapDecryptor.dmg` there.

Windows native builds must run on Windows; the macOS build instructions do not produce a Windows executable.

## Troubleshooting

Application logs are written to `~/.robocap_decryptor/logs/`. The resumable bulk script's completion record is stored as `.robocap-decrypt-done.txt` in the selected output folder. Neither contains key material.
