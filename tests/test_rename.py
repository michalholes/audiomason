from audiomason.rename import extract_track_num, natural_sort


def test_extract_track_num():
    assert extract_track_num("01.mp3") == 1
    assert extract_track_num("track_12_something.mp3") == 12
    assert extract_track_num("no_number.mp3") is None

def test_natural_sort(tmp_path):
    files = [
        tmp_path / "10.mp3",
        tmp_path / "2.mp3",
        tmp_path / "01.mp3",
        tmp_path / "abc.mp3",
    ]
    out = natural_sort(files)
    assert [p.name for p in out] == ["01.mp3", "2.mp3", "10.mp3", "abc.mp3"]
