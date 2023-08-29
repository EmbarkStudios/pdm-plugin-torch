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


def tmpdir_project(project_name, dest, pdm):
    source = FIXTURES / project_name
    copytree(source, dest)
    pdm(["config", "cache_dir", str("/tmp/.pdm_cache")], dest)


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

        tmpdir_project("cpu-only", tmpdir, pdm)
        with pytest.raises(subprocess.CalledProcessError):
            pdm(["torch", "-v", "lock", "--check"], tmpdir)

    @staticmethod
    def test_lock_plugin_check_succeeds(tmpdir, pdm):
        tmpdir_project("cpu-only", tmpdir, pdm)
        pdm(["torch", "-v", "lock"], tmpdir)
        pdm(["torch", "-v", "lock", "--check"], tmpdir)

    @staticmethod
    def test_install_fails(tmpdir, pdm):
        import subprocess

        tmpdir_project("cpu-only", tmpdir, pdm)
        with pytest.raises(subprocess.CalledProcessError):
            pdm(["torch", "-v", "install", "cpu"], tmpdir)

    @staticmethod
    def test_install_succeeds(tmpdir, pdm):
        tmpdir_project("cpu-only", tmpdir, pdm)
        pdm(["torch", "-vv", "lock"], tmpdir)
        pdm(["torch", "-vv", "install", "cpu"], tmpdir)

    @staticmethod
    def test_import(tmpdir, pdm):
        tmpdir_project("cpu-only", tmpdir, pdm)
        pdm(["torch", "-v", "lock"], tmpdir)
        pdm(["torch", "-v", "install", "cpu"], tmpdir)
        pdm(["run", "python", "-c", "'import torch'"], tmpdir)
