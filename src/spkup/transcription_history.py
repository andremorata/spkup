from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptionHistoryEntry:
    id: str
    text: str


class TranscriptionHistory:
    def __init__(self, max_entries: int = 5) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")

        self._max_entries = max_entries
        self._entries: list[TranscriptionHistoryEntry] = []
        self._next_id = 1

    def add(self, text: str) -> TranscriptionHistoryEntry:
        entry = TranscriptionHistoryEntry(id=str(self._next_id), text=text)
        self._next_id += 1

        self._entries.insert(0, entry)
        del self._entries[self._max_entries :]
        return entry

    def list_entries(self) -> list[TranscriptionHistoryEntry]:
        return list(self._entries)

    def delete(self, entry_id: str) -> bool:
        for index, entry in enumerate(self._entries):
            if entry.id == entry_id:
                del self._entries[index]
                return True
        return False

    def clear(self) -> None:
        self._entries.clear()
