import os
import shutil
import subprocess

from pathlib import Path
from unittest import mock

import pytest

from tests import FIXTURES


PLUGIN_DIR = os.path.abspath(f"{__file__}/../..")


def copytree(src: Path, dst: Path) -> None:
    if not dst.exists():
        dst.mkdir(parents=True)
    for subpath in src.iterdir():
        if subpath.is_dir():
            copytree(subpath, dst / subpath.name)
        else:
            shutil.copy2(subpath, dst)


def make_entry_point(plugin):
    ret = mock.Mock()
    ret.load.return_value = plugin
    return ret


def tmpdir_project(project_name, dest):
    source = FIXTURES / project_name
    copytree(source, dest)


@pytest.fixture
def pdm(request):
    pdm_name = request.config.getoption("--pdm-bin")

    def _invoker(args, dir):
        output = subprocess.check_output([pdm_name, *args], cwd=dir)
        return output

    return _invoker


class TestPdmVariants:
    @staticmethod
    def test_install_plugin(tmpdir, pdm):
        output = pdm(["self", "add", PLUGIN_DIR], tmpdir)
        assert output == b"Installation succeeds.\n"

    @staticmethod
    def test_lock_check_fails(tmpdir, pdm):
        import subprocess

        tmpdir_project("cpu-only", tmpdir)
        with pytest.raises(subprocess.CalledProcessError):
            pdm(["torch", "lock", "--check"], tmpdir)

    @staticmethod
    def test_lock_plugin_check_succeeds(tmpdir, pdm):
        tmpdir_project("cpu-only", tmpdir)
        pdm(["torch", "lock"], tmpdir)
        pdm(["torch", "lock", "--check"], tmpdir)

    @staticmethod
    def test_install_fails(tmpdir, pdm):
        import subprocess

        tmpdir_project("cpu-only", tmpdir)
        with pytest.raises(subprocess.CalledProcessError):
            pdm(["torch", "install", "cpu"], tmpdir)

    @staticmethod
    def test_install_succeeds(tmpdir, pdm):
        tmpdir_project("cpu-only", tmpdir)
        pdm(["torch", "lock"], tmpdir)
        pdm(["torch", "install", "cpu"], tmpdir)
