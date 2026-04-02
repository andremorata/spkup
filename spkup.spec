"""PyInstaller baseline for building the Windows spkup release artifact.

Build command:
    pyinstaller --clean spkup.spec

This baseline targets the current frozen Windows release contract: a practical
onedir build that can be zipped and attached to a release.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_root = Path(SPECPATH).resolve()
src_root = project_root / "src"
sys.path.insert(0, str(src_root))

spkup_datas, spkup_binaries, spkup_hiddenimports = collect_all("spkup")
fw_datas, fw_binaries, fw_hiddenimports = collect_all("faster_whisper")
ct_datas, ct_binaries, ct_hiddenimports = collect_all("ctranslate2")
hf_datas, hf_binaries, hf_hiddenimports = collect_all("huggingface_hub")
av_datas, av_binaries, av_hiddenimports = collect_all("av")

datas = spkup_datas + fw_datas + ct_datas + hf_datas + av_datas
binaries = spkup_binaries + fw_binaries + ct_binaries + hf_binaries + av_binaries
hiddenimports = (
    spkup_hiddenimports
    + fw_hiddenimports
    + ct_hiddenimports
    + hf_hiddenimports
    + av_hiddenimports
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
    excludes=[],
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    exclude_binaries=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="spkup",
)
