"""Tests for write_adms_changelog."""
import pytest

from write_adms_changelog import FALLBACK_MESSAGE, added_pins, build_message, fragments_to_write, split_diff_by_file

NET_DIFF = """\
diff --git a/datadog_checks_dev/pyproject.toml b/datadog_checks_dev/pyproject.toml
index 5555555..6666666 100644
--- a/datadog_checks_dev/pyproject.toml
+++ b/datadog_checks_dev/pyproject.toml
@@ -30,3 +30,3 @@ dependencies = [
-    "virtualenv>=20.0.0",
+    "virtualenv>=21.14.5",
diff --git a/mongo/pyproject.toml b/mongo/pyproject.toml
index 1111111..2222222 100644
--- a/mongo/pyproject.toml
+++ b/mongo/pyproject.toml
@@ -40,3 +40,3 @@ deps = [
-    "pymongo[srv]==4.18.2",
+    "pymongo[srv]==4.18.3",
diff --git a/snmp/pyproject.toml b/snmp/pyproject.toml
index 3333333..4444444 100644
--- a/snmp/pyproject.toml
+++ b/snmp/pyproject.toml
@@ -40,3 +40,3 @@ deps = [
-    "pyasn1==0.6.1",
+    "pyasn1==0.6.2",
diff --git a/pyproject.toml b/pyproject.toml
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -1,1 +1,1 @@
+    "hatch==1.16.0",
diff --git a/.builders/pyproject.toml b/.builders/pyproject.toml
--- a/.builders/pyproject.toml
+++ b/.builders/pyproject.toml
@@ -1,1 +1,1 @@
+    "uv==0.9.0",
diff --git a/mongo/tests/compose/pyproject.toml b/mongo/tests/compose/pyproject.toml
--- a/mongo/tests/compose/pyproject.toml
+++ b/mongo/tests/compose/pyproject.toml
@@ -1,1 +1,1 @@
+    "pymongo==4.18.3",
"""


def test_added_pins_reads_new_versions_only():
    patch = '-    "pymongo==4.18.2",\n+    "pymongo[srv]==4.18.3",\n+    "virtualenv>=21.14.5",\n+version = "1.2.3"\n'
    assert added_pins(patch) == {"pymongo": "4.18.3", "virtualenv": "21.14.5"}


@pytest.mark.parametrize(
    "pins, expected",
    [
        ({}, FALLBACK_MESSAGE),
        ({"pymongo": "4.18.3"}, "Bump `pymongo` to 4.18.3."),
        ({"tuf": "6.0.0", "dnspython": "2.8.1"}, "Bump `dnspython` to 2.8.1 and `tuf` to 6.0.0."),
        ({"c": "3", "a": "1", "b": "2"}, "Bump `a` to 1, `b` to 2, and `c` to 3."),
    ],
)
def test_build_message(pins, expected):
    assert build_message(pins) == expected


def test_fragments_to_write_covers_changed_packages_without_a_fragment(tmp_path):
    (tmp_path / "snmp" / "changelog.d").mkdir(parents=True)
    (tmp_path / "snmp" / "changelog.d" / "25968.security").write_text("Already written.\n")

    fragments = fragments_to_write(split_diff_by_file(NET_DIFF), 25968, tmp_path)

    assert fragments == {
        tmp_path / "datadog_checks_dev" / "changelog.d" / "25968.security": "Bump `virtualenv` to 21.14.5.",
        tmp_path / "mongo" / "changelog.d" / "25968.security": "Bump `pymongo` to 4.18.3.",
    }
