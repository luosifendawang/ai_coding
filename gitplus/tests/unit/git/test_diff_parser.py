from gitplus.git.parser import parse_git_patch, parse_numstat_z
from gitplus.models.diff import FileChangeStatus


def test_parse_modified_file_patch() -> None:
    patch = """diff --git a/src/main.py b/src/main.py
index 1111111..2222222 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1 +1,2 @@
 print("hello")
+print("world")
"""

    files = parse_git_patch(patch)

    assert len(files) == 1
    assert files[0].status == FileChangeStatus.MODIFIED
    assert files[0].new_path == "src/main.py"
    assert files[0].additions == 1
    assert files[0].deletions == 0
    assert files[0].extension == ".py"


def test_parse_added_and_deleted_files() -> None:
    patch = """diff --git a/src/new.py b/src/new.py
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/src/new.py
@@ -0,0 +1 @@
+new
diff --git a/src/old.py b/src/old.py
deleted file mode 100644
index 1111111..0000000
--- a/src/old.py
+++ /dev/null
@@ -1 +0,0 @@
-old
"""

    files = parse_git_patch(patch)

    assert files[0].status == FileChangeStatus.ADDED
    assert files[0].is_new_file is True
    assert files[1].status == FileChangeStatus.DELETED
    assert files[1].is_deleted_file is True


def test_parse_renamed_and_copied_files() -> None:
    patch = """diff --git a/old name.py b/new name.py
similarity index 98%
rename from old name.py
rename to new name.py
diff --git a/source.py b/copy.py
similarity index 100%
copy from source.py
copy to copy.py
"""

    files = parse_git_patch(patch)

    assert files[0].status == FileChangeStatus.RENAMED
    assert files[0].old_path == "old name.py"
    assert files[0].new_path == "new name.py"
    assert files[0].is_renamed is True
    assert files[1].status == FileChangeStatus.COPIED
    assert files[1].is_copied is True


def test_parse_binary_file_patch() -> None:
    patch = """diff --git a/assets/logo.png b/assets/logo.png
index 1111111..2222222 100644
Binary files a/assets/logo.png and b/assets/logo.png differ
"""

    files = parse_git_patch(patch)

    assert files[0].is_binary is True
    assert files[0].patch == "[gitplus: binary file diff omitted]"
    assert files[0].extension == ".png"


def test_parse_numstat_z_for_normal_and_rename() -> None:
    output = "3\t1\tsrc/main.py\0 2\t0\0old.py\0new.py\0"

    stats = parse_numstat_z(output)

    assert stats["src/main.py"] == (3, 1)
    assert stats["new.py"] == (2, 0)

