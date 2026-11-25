import pytest


@pytest.fixture(autouse=True)
def _faster_whisper_engine(monkeypatch):
    """Run the faster-whisper path by default, even on Apple Silicon hosts.

    MLX tests opt in by patching ``uses_mlx_engine`` back to True.
    """
    monkeypatch.setattr("spkup.transcriber.uses_mlx_engine", lambda: False)
    monkeypatch.setattr("spkup.model_manager.uses_mlx_engine", lambda: False)
