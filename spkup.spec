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


def collect_nvidia_wheel_binaries() -> list[tuple[str, str]]:
    collected: list[tuple[str, str]] = []
    seen: set[Path] = set()

    for entry in map(Path, sys.path):
        nvidia_root = entry / "nvidia"
        if not nvidia_root.is_dir():
            continue

        for bin_dir in sorted(nvidia_root.glob("*/bin")):
            if not bin_dir.is_dir():
                continue

            destination = str(Path("nvidia") / bin_dir.parent.name / "bin")
            for file_path in sorted(bin_dir.iterdir()):
                if not file_path.is_file():
                    continue

                resolved = file_path.resolve()
                if resolved in seen:
                    continue

                seen.add(resolved)
                collected.append((str(resolved), destination))

    return collected

spkup_datas, spkup_binaries, spkup_hiddenimports = collect_all("spkup")
fw_datas, fw_binaries, fw_hiddenimports = collect_all("faster_whisper")
ct_datas, ct_binaries, ct_hiddenimports = collect_all("ctranslate2")
hf_datas, hf_binaries, hf_hiddenimports = collect_all("huggingface_hub")
av_datas, av_binaries, av_hiddenimports = collect_all("av")

datas = spkup_datas + fw_datas + ct_datas + hf_datas + av_datas
binaries = (
    spkup_binaries
    + fw_binaries
    + ct_binaries
    + hf_binaries
    + av_binaries
    + collect_nvidia_wheel_binaries()
)
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
