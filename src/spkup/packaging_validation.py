from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path


REQUIRED_CUDA_DLL_PATTERNS: tuple[str, ...] = (
    "cublas64_12.dll",
    "cublasLt64_12.dll",
    "cudnn64_9.dll",
    "cudnn_ops64_9.dll",
    "cudnn_cnn64_9.dll",
    "nvrtc64_*.dll",
)


def missing_cuda_runtime_dlls(bundle_dir: Path) -> list[str]:
    if not bundle_dir.is_dir():
        raise FileNotFoundError(f"Bundle directory does not exist: {bundle_dir}")

    dll_names = {path.name.lower() for path in bundle_dir.rglob("*.dll")}
    missing: list[str] = []
    for pattern in REQUIRED_CUDA_DLL_PATTERNS:
        normalized = pattern.lower()
        if not any(fnmatch.fnmatchcase(name, normalized) for name in dll_names):
            missing.append(pattern)
    return missing


def validate_cuda_runtime_dlls(bundle_dir: Path) -> None:
    missing = missing_cuda_runtime_dlls(bundle_dir)
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"Frozen bundle is missing CUDA runtime DLLs required for GPU "
            f"transcription: {joined}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate that a PyInstaller spkup bundle includes CUDA DLLs."
    )
    parser.add_argument("bundle_dir", type=Path)
    args = parser.parse_args(argv)

    try:
        validate_cuda_runtime_dlls(args.bundle_dir)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"CUDA runtime DLL validation passed: {args.bundle_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
