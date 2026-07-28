from gitpulse.git.parser import parse_porcelain_status_z


def test_parse_porcelain_status_z_handles_common_statuses() -> None:
    output = "M  src/main.py\0 M src/with space.py\0A  中文/新文件.py\0?? temp.txt\0UU conflict.py\0"

    entries = parse_porcelain_status_z(output)

    assert [entry.path for entry in entries] == [
        "src/main.py",
        "src/with space.py",
        "中文/新文件.py",
        "temp.txt",
        "conflict.py",
    ]
    assert entries[0].index_status == "M"
    assert entries[1].worktree_status == "M"
    assert entries[3].index_status == "?"
    assert entries[4].is_conflict is True


def test_parse_porcelain_status_z_handles_renames() -> None:
    output = "R  new name.py\0old name.py\0"

    entries = parse_porcelain_status_z(output)

    assert entries[0].path == "new name.py"
    assert entries[0].original_path == "old name.py"

