"""
tools/report_manifest.py testleri.

Manifest yanlis alarm verirse (satir sonu, sira) kimse ona guvenmez ve
kontrol kapatilir; gercek farki kacirirsa varlik sebebi kalmaz. Iki yon de
test ediliyor.
"""
import report_manifest as rm


def _reports(tmp_path, files, dirname="reports"):
    d = tmp_path / dirname
    d.mkdir()
    for name, data in files.items():
        (d / name).write_bytes(data)
    return d


def test_crlf_and_lf_hash_the_same(tmp_path):
    a = _reports(tmp_path, {"r.md": b"x\r\ny\r\n"}, dirname="windows")
    b = _reports(tmp_path, {"r.md": b"x\ny\n"}, dirname="linux")

    assert rm.compute(a) == rm.compute(b)


def test_only_md_and_csv_are_covered(tmp_path):
    d = _reports(tmp_path, {"a.md": b"1", "b.csv": b"2", "c.png": b"3", "d.txt": b"4"})

    assert list(rm.compute(d)) == ["a.md", "b.csv"]


def test_update_then_check_passes(tmp_path):
    d = _reports(tmp_path, {"a.md": b"1", "b.csv": b"2"})

    assert rm.main(["--update"], reports=d) == 0
    assert rm.main([], reports=d) == 0
    # manifest kendi kendini kapsamiyor
    assert rm.MANIFEST_NAME not in rm.read(d / rm.MANIFEST_NAME)


def test_check_detects_changed_missing_and_extra(tmp_path, capsys):
    d = _reports(tmp_path, {"a.md": b"1", "b.csv": b"2", "c.csv": b"3"})
    rm.main(["--update"], reports=d)

    (d / "a.md").write_bytes(b"1 ama degisti")
    (d / "b.csv").unlink()
    (d / "yeni.csv").write_bytes(b"4")

    assert rm.main([], reports=d) == 1
    out = capsys.readouterr().out
    assert "degisti a.md" in out
    assert "eksik   b.csv" in out
    assert "fazla   yeni.csv" in out
    assert "c.csv" not in out


def test_check_without_manifest_fails(tmp_path):
    d = _reports(tmp_path, {"a.md": b"1"})

    assert rm.main([], reports=d) == 1


def test_manifest_file_is_lf_and_sha256sum_format(tmp_path):
    d = _reports(tmp_path, {"a.md": b"1"})
    rm.main(["--update"], reports=d)

    text = (d / rm.MANIFEST_NAME).read_bytes()
    assert b"\r" not in text
    h, name = text.decode().rstrip("\n").split("  ")
    assert len(h) == 64 and name == "a.md"
