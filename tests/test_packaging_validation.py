from pathlib import Path

import pytest

from spkup.packaging_validation import (
    REQUIRED_CUDA_DLL_PATTERNS,
    missing_cuda_runtime_dlls,
    validate_cuda_runtime_dlls,
)


def _touch_dll(bundle_dir: Path, relative_path: str) -> None:
    path = bundle_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"dll")


def test_missing_cuda_runtime_dlls_reports_absent_required_files(tmp_path: Path) -> None:
    _touch_dll(tmp_path, "_internal/ctranslate2/ctranslate2.dll")

    assert missing_cuda_runtime_dlls(tmp_path) == list(REQUIRED_CUDA_DLL_PATTERNS)


def test_validate_cuda_runtime_dlls_accepts_gpu_bundle(tmp_path: Path) -> None:
    _touch_dll(tmp_path, "_internal/nvidia/cublas/bin/cublas64_12.dll")
    _touch_dll(tmp_path, "_internal/nvidia/cublas/bin/cublasLt64_12.dll")
    _touch_dll(tmp_path, "_internal/nvidia/cudnn/bin/cudnn64_9.dll")
    _touch_dll(tmp_path, "_internal/nvidia/cudnn/bin/cudnn_ops64_9.dll")
    _touch_dll(tmp_path, "_internal/nvidia/cudnn/bin/cudnn_cnn64_9.dll")
    _touch_dll(tmp_path, "_internal/nvidia/cuda_nvrtc/bin/nvrtc64_120_0.dll")

    validate_cuda_runtime_dlls(tmp_path)


def test_validate_cuda_runtime_dlls_rejects_cpu_only_bundle(tmp_path: Path) -> None:
    _touch_dll(tmp_path, "_internal/ctranslate2/ctranslate2.dll")

    with pytest.raises(RuntimeError, match="missing CUDA runtime DLLs"):
        validate_cuda_runtime_dlls(tmp_path)


def test_missing_cuda_runtime_dlls_requires_existing_bundle(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        missing_cuda_runtime_dlls(tmp_path / "missing")
