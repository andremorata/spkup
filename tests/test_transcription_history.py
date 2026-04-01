from spkup.transcription_history import TranscriptionHistory


def test_add_and_list_one_item():
    history = TranscriptionHistory()

    entry = history.add("hello world")

    assert history.list_entries() == [entry]
    assert entry.id == "1"
    assert entry.text == "hello world"


def test_keep_only_last_five_entries():
    history = TranscriptionHistory()

    for index in range(6):
        history.add(f"item {index}")

    entries = history.list_entries()

    assert len(entries) == 5
    assert [entry.text for entry in entries] == [
        "item 5",
        "item 4",
        "item 3",
        "item 2",
        "item 1",
    ]


def test_newest_entries_come_first():
    history = TranscriptionHistory()

    first = history.add("first")
    second = history.add("second")
    third = history.add("third")

    assert history.list_entries() == [third, second, first]


def test_delete_existing_item():
    history = TranscriptionHistory()

    first = history.add("first")
    second = history.add("second")

    deleted = history.delete(first.id)

    assert deleted is True
    assert history.list_entries() == [second]


def test_delete_unknown_item_is_safe():
    history = TranscriptionHistory()

    first = history.add("first")
    second = history.add("second")

    deleted = history.delete("missing")

    assert deleted is False
    assert history.list_entries() == [second, first]


def test_unicode_text_is_preserved():
    history = TranscriptionHistory()

    text = "Ola, mundo. Cafe, acao, \u65e5\u672c\u8a9e, \U0001f600"
    entry = history.add(text)

    assert history.list_entries()[0] == entry
    assert entry.text == text


def test_duplicate_texts_are_distinct_entries():
    history = TranscriptionHistory()

    first = history.add("same")
    second = history.add("same")

    assert first != second
    assert first.id != second.id
    assert history.list_entries() == [second, first]
