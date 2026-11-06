"""Launcher contract tests; actual GTK loading is tested in a desktop VM."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InputModuleLauncherTests(unittest.TestCase):
    def test_cache_arguments_environment_and_exit_status(self):
        for triplet in ("x86_64-linux-gnu", "aarch64-linux-gnu"):
            with self.subTest(triplet=triplet), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                snap = root / "snap with spaces"
                data = root / "user data"
                lib = snap / "usr/lib" / triplet
                modules = lib / "gtk-3.0/3.0.0/immodules"
                modules.mkdir(parents=True)
                (modules / "im-fcitx5.so").touch()
                (modules / "im-wayland.so").touch()
                query = lib / "libgtk-3-0t64/gtk-query-immodules-3.0"
                query.parent.mkdir()
                query.write_text(
                    "#!/usr/bin/python3\n"
                    "import json, os, sys\n"
                    "print(json.dumps(sys.argv[1:]))\n"
                    "sys.exit(int(os.environ.get('QUERY_STATUS', '0')))\n"
                )
                query.chmod(0o755)
                launcher = root / "launcher"
                launcher.write_text(
                    (ROOT / "snap/local/im-modules").read_text().replace(
                        "@ARCH_TRIPLET@", triplet
                    )
                )
                launcher.chmod(0o755)
                child = root / "child.py"
                child.write_text(
                    "import json, os, pathlib, sys\n"
                    "print(json.dumps({'args': sys.argv[1:], "
                    "'module': os.environ.get('GTK_IM_MODULE'), "
                    "'other': os.environ.get('UNCHANGED'), "
                    "'path': os.environ['GTK_PATH'], "
                    "'cache': pathlib.Path(os.environ['GTK_IM_MODULE_FILE']).read_text()}))\n"
                    "sys.exit(23)\n"
                )
                env = dict(os.environ, SNAP=str(snap), SNAP_USER_DATA=str(data),
                           GTK_IM_MODULE="fcitx", GTK_PATH="/host/gtk",
                           GTK_IM_MODULE_FILE="/host/cache", UNCHANGED="preserved")
                args = ["space separated", "literal*$", ""]
                result = subprocess.run(
                    [str(launcher), "/usr/bin/python3", str(child), *args],
                    env=env, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 23, result.stderr)
                actual = json.loads(result.stdout)
                self.assertEqual(actual["args"], args)
                self.assertEqual(actual["module"], "fcitx")
                self.assertEqual(actual["other"], "preserved")
                self.assertEqual(actual["path"], str(lib / "gtk-3.0"))
                self.assertEqual(json.loads(actual["cache"]),
                                 [str(modules / "im-fcitx5.so"), str(modules / "im-wayland.so")])

                # A failed refresh must not replace the valid cache or run the app.
                cache = data / "gtk-immodules.cache"
                before = cache.read_bytes()
                result = subprocess.run(
                    [str(launcher), "/bin/echo", "must not run"],
                    env=dict(env, QUERY_STATUS="7"), capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 7)
                self.assertEqual(result.stdout, "")
                self.assertEqual(cache.read_bytes(), before)
                self.assertEqual(list(data.iterdir()), [cache])

                # Do not force a framework when the session has not chosen one.
                env.pop("GTK_IM_MODULE")
                result = subprocess.run(
                    [str(launcher), "/usr/bin/python3", str(child)],
                    env=env, capture_output=True, text=True,
                )
                self.assertEqual(json.loads(result.stdout)["module"], None)


if __name__ == "__main__":
    unittest.main()
