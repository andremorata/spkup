"""PyInstaller baseline for building the macOS ARM64 spkup release artifact.

Build command:
    pyinstaller --clean spkup-macos.spec

This spec omits Windows-only NVIDIA CUDA runtime collection. Transcription runs
on the Apple GPU through mlx-whisper; faster-whisper stays bundled for its
Silero VAD. torch is excluded: mlx-whisper only imports it in its checkpoint
conversion script, which spkup never runs.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


project_root = Path(SPECPATH).resolve()
src_root = project_root / "src"
sys.path.insert(0, str(src_root))

from spkup import __version__

spkup_datas, spkup_binaries, spkup_hiddenimports = collect_all("spkup")
fw_datas, fw_binaries, fw_hiddenimports = collect_all("faster_whisper")
ct_datas, ct_binaries, ct_hiddenimports = collect_all("ctranslate2")
hf_datas, hf_binaries, hf_hiddenimports = collect_all("huggingface_hub")
av_datas, av_binaries, av_hiddenimports = collect_all("av")
mlx_datas, mlx_binaries, mlx_hiddenimports = collect_all("mlx")
mw_datas, mw_binaries, mw_hiddenimports = collect_all("mlx_whisper")
# scipy (pulled in by mlx_whisper.timing) imports its vendored array-api shims by
# name at runtime, which PyInstaller's static analysis cannot see.
scipy_hiddenimports = collect_submodules("scipy._external.array_api_compat")

datas = spkup_datas + fw_datas + ct_datas + hf_datas + av_datas + mlx_datas + mw_datas
binaries = (
    spkup_binaries + fw_binaries + ct_binaries + hf_binaries + av_binaries
    + mlx_binaries + mw_binaries
)
hiddenimports = (
    spkup_hiddenimports
    + fw_hiddenimports
    + ct_hiddenimports
    + hf_hiddenimports
    + av_hiddenimports
    + mlx_hiddenimports
    + mw_hiddenimports
    + scipy_hiddenimports
)

a = Analysis(
    [str(src_root / "spkup" / "__main__.py")],
    pathex=[str(src_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name="spkup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    exclude_binaries=True,
    target_arch="arm64",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="spkup",
)

app = BUNDLE(
    coll,
    name="spkup.app",
    icon=str(src_root / "spkup" / "resources" / "spkup.icns"),
    bundle_identifier="dev.andremorata.spkup",
    info_plist={
        "CFBundleName": "spkup",
        "CFBundleDisplayName": "spkup",
        "CFBundleShortVersionString": __version__,
        "CFBundleVersion": __version__,
        "LSUIElement": True,
        "NSMicrophoneUsageDescription": (
            "spkup records microphone audio while the push-to-talk trigger is active."
        ),
    },
)
