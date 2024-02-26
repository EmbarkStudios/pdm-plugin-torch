"""Plugin main file."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

import tomlkit
from pdm import __version__, termui
from pdm._types import RepositoryConfig
from pdm.cli.commands.base import BaseCommand
from pdm.cli.commands.export import Command as PDMExportCommand
from pdm.cli.utils import fetch_hashes, format_lockfile, format_resolution_impossible
from pdm.core import Core
from pdm.formats import FORMATS
from pdm.models.candidates import Candidate
from pdm.models.repositories import BaseRepository, LockedRepository
from pdm.models.requirements import Requirement, parse_requirement, strip_extras
from pdm.models.specifiers import PySpecSet, get_specifier
from pdm.project import Project
from pdm.resolver import resolve
from pdm.resolver.providers import (
    BaseProvider,
    EagerUpdateProvider,
    ReusePinProvider,
)
from pdm.termui import Verbosity
from pdm.utils import atomic_open_for_write, expand_env_vars_in_auth, normalize_name
from resolvelib.reporters import BaseReporter
from resolvelib.resolvers import ResolutionImpossible, ResolutionTooDeep, Resolver

from pdm_plugin_torch.config import Configuration

is_pdm212 = PySpecSet(">=2.12").contains(__version__.__version__)
is_pdm210 = PySpecSet(">=2.10").contains(__version__.__version__)
is_pdm29 = PySpecSet(">=2.9").contains(__version__.__version__)
is_pdm28 = PySpecSet(">=2.8").contains(__version__.__version__)


def sources(project: Project, source_list: list) -> list[RepositoryConfig]:
    result: dict[str, RepositoryConfig] = {}
    for source in project.pyproject.settings.get("source", []):
        result[source["name"]] = RepositoryConfig(**source, config_prefix="pypi")

    for source in source_list:
        result[source["name"]] = RepositoryConfig(**source, config_prefix="torch")

    def merge_sources(other_sources: Iterable[tuple[str, RepositoryConfig]]) -> None:
        for name, source in other_sources:
            source.name = name
            if name in result:
                result[name].passive_update(source)
            else:
                result[name] = source

    if not project.config.get("pypi.ignore_stored_index", False):
        if "pypi" not in result:  # put pypi source at the beginning
            result = {"pypi": project.default_source, **result}
        else:
            result["pypi"].passive_update(project.default_source)
        merge_sources(project.project_config.iter_sources())
        merge_sources(project.global_config.iter_sources())

    for source in result.values():
        assert source.url, "Source URL must not be empty"
        source.url = expand_env_vars_in_auth(source.url)

    return list(result.values())


def get_provider(
    project: Project,
    raw_sources: list,
    strategy: str = "all",
    for_install: bool = False,
    lockfile: dict = None,
    tracked_names: Iterable[str] | None = None,
    allow_prereleases: bool = False,
) -> BaseProvider:
    """
    Build a provider class for resolver.

    :param strategy: the resolve strategy
    :param tracked_names: the names of packages that needs to update
    :param for_install: if the provider is for install
    :returns: The provider object
    """

    repository = get_repository(
        project, raw_sources, for_install=for_install, lockfile=lockfile
    )

    if not is_pdm212:
        overrides = {
            normalize_name(k): v
            for k, v in project.pyproject.resolution_overrides.items()
        }

    locked_repository: LockedRepository | None = None
    if strategy != "all" or for_install:
        try:
            locked_repository = LockedRepository(lockfile, sources, project.environment)
        except Exception as ex:  # pylint: disable=W0718
            if for_install:
                raise ex
            project.core.ui.echo(
                "Unable to reuse the lock file as it is not compatible with PDM",
                style="warning",
                err=True,
            )

    if is_pdm212:
        additional_base_provider_args = []
    else:
        additional_base_provider_args = [allow_prereleases, overrides]
    if locked_repository is None:
        return BaseProvider(repository, *additional_base_provider_args)
    if for_install:
        return BaseProvider(locked_repository, *additional_base_provider_args)

    provider_class = ReusePinProvider if strategy == "reuse" else EagerUpdateProvider
    tracked_names = [strip_extras(name)[0] for name in tracked_names or ()]

    return provider_class(
        locked_repository.all_candidates,
        tracked_names,
        repository,
        *additional_base_provider_args,
    )


def get_repository(
    project: Project,
    raw_sources: list,
    cls: type[BaseRepository] | None = None,
    for_install: bool = False,  # pylint: disable=W0613
    lockfile: dict = None,  # pylint: disable=W0613
) -> BaseRepository:
    """Get the repository object."""
    if cls is None:
        cls = project.core.repository_class

    fixed_sources = sources(project, raw_sources)
    return cls(
        fixed_sources,
        project.environment,
    )


def do_lock(
    project: Project,
    raw_sources: list,
    strategy: str = "all",
    requirements: list[Requirement] | None = None,
) -> dict[str, Candidate]:
    """Performs the locking process and update lockfile."""

    provider = get_provider(project, raw_sources, strategy)
    resolve_max_rounds = int(project.config["strategy.resolve_max_rounds"])
    ui = project.core.ui
    with ui.logging("lock"):
        # The context managers are nested to ensure the spinner is stopped before
        # any message is thrown to the output.
        try:
            with ui.open_spinner(title="Resolving dependencies") as spin:
                reporter = project.get_reporter(requirements, None, spin)
                resolver: Resolver = project.core.resolver_class(provider, reporter)
                mapping, dependencies = resolve(
                    resolver,
                    requirements,
                    project.environment.python_requires,
                    resolve_max_rounds,
                )

                spin.update("Fetching hashes for resolved packages...")
                fetch_hashes(provider.repository, mapping)

        except ResolutionTooDeep:
            ui.echo(f"{termui.Emoji.LOCK} Lock failed", err=True)
            ui.echo(
                "The dependency resolution exceeds the maximum loop depth of "
                f"{resolve_max_rounds}, there may be some circular dependencies "
                "in your project. Try to solve them or increase the "
                f"[green]`strategy.resolve_max_rounds`[/] config.",
                err=True,
            )
            raise
        except ResolutionImpossible as err:
            ui.echo(f"{termui.Emoji.LOCK} Lock failed", err=True)
            ui.echo(format_resolution_impossible(err), err=True)
            raise ResolutionImpossible("Unable to find a resolution") from None
        else:
            if is_pdm210:
                from pdm.project.lockfile import (  # pylint: disable=C0415
                    FLAG_STATIC_URLS,
                )

                data = format_lockfile(
                    project,
                    mapping,
                    dependencies,
                    groups=[],
                    strategy={FLAG_STATIC_URLS},
                )

            elif is_pdm29:
                data = format_lockfile(project, mapping, dependencies, static_urls=True)  # pylint: disable=E1123, E1120

            elif is_pdm28:
                data = format_lockfile(project, mapping, dependencies, static_urls=True)  # pylint: disable=E1123, E1120

            else:
                data = format_lockfile(project, mapping, dependencies)  # pylint: disable=E1123, E1120

            ui.echo(f"{termui.Emoji.LOCK} Lock successful")
            return data


def write_lockfile(
    project: Project, lock_name: str, toml_data: dict, show_message: bool = True
) -> None:
    """Write the lockfile for this project.

    Args:
        project: the project to write the lockfile for.
        lock_name: name of the lock file relative to the repository root.
        toml_data: the data to write to the lock file.
        show_message: whether to show a log message to the console.
    """
    toml_data["metadata"] = project.get_lock_metadata()
    lockfile_file = project.root / lock_name

    with atomic_open_for_write(lockfile_file) as fp:
        tomlkit.dump(toml_data, fp)  # type: ignore
    if show_message:
        project.core.ui.echo(f"Torch locks are written to [success]{lockfile_file}[/].")


def resolve_candidates_from_lockfile(
    project: Project,
    requirements: Iterable[Requirement],
    raw_sources,
    lockfile: dict,
    for_install: bool = True,  # pylint: disable=W0613
) -> dict[str, Candidate]:
    ui = project.core.ui
    resolve_max_rounds = int(project.config["strategy.resolve_max_rounds"])
    reqs = [
        req
        for req in requirements
        if not req.marker or req.marker.evaluate(project.environment.marker_environment)
    ]
    with ui.logging("install-resolve"):
        with ui.open_spinner("Resolving packages from lockfile...") as spinner:
            reporter = BaseReporter()
            provider = get_provider(
                project, raw_sources, for_install=for_install, lockfile=lockfile
            )
            resolver: Resolver = project.core.resolver_class(provider, reporter)
            mapping, *_ = resolve(
                resolver,
                reqs,
                project.environment.python_requires,
                resolve_max_rounds,
            )
            spinner.update("Fetching hashes for resolved packages...")
            fetch_hashes(provider.repository, mapping)

    return mapping


def do_sync(
    project: Project,
    *,
    raw_sources: list,
    requirements: list[Requirement] | None = None,
    lockfile: dict,
) -> None:
    """Synchronize project"""

    candidates = resolve_candidates_from_lockfile(
        project, requirements, raw_sources, lockfile
    )

    handler = project.core.synchronizer_class(
        candidates,
        project.environment,
        clean=False,
        dry_run=False,
        no_editable=True,
        install_self=False,
        reinstall=False,
        only_keep=False,
        fail_fast=True,
    )

    with project.core.ui.logging("install"):
        handler.synchronize()


def read_lockfile(project: Project, lock_name: str) -> None:
    lockfile_file = project.root / lock_name

    data = tomlkit.parse(lockfile_file.read_text("utf-8"))
    return data


def is_lockfile_compatible(project: Project, lock_name: str) -> bool:
    lockfile_file = project.root / lock_name
    if not lockfile_file.exists():
        return True

    lockfile = read_lockfile(project, lock_name)
    lockfile_version = str(lockfile.get("metadata", {}).get("lock_version", ""))
    if not lockfile_version:
        return False

    if "." not in lockfile_version:
        lockfile_version += ".0"

    accepted = get_specifier(f"~={lockfile_version}")
    return accepted.contains(project.lockfile.spec_version)


def is_lockfile_hash_match(project: Project, lock_name: str) -> bool:
    lockfile_file = project.root / lock_name
    if not lockfile_file.exists():
        return False

    lockfile = read_lockfile(project, lock_name)
    hash_in_lockfile = str(lockfile.get("metadata", {}).get("content_hash", ""))
    if not hash_in_lockfile:
        return False

    algo, hash_value = hash_in_lockfile.split(":")
    content_hash = project.pyproject.content_hash(algo)

    return content_hash == hash_value


def check_lockfile(project: Project, lock_name: str) -> str | None:
    """Check if the lock file exists and is up to date. Return the update strategy."""
    lockfile_file = project.root / lock_name
    if not lockfile_file.exists():
        project.core.ui.echo("Lock file does not exist", style="warning", err=True)
        return False
    elif not is_lockfile_compatible(project, lock_name):
        project.core.ui.echo(
            "Lock file version is not compatible with PDM, installation may fail",
            style="yellow",
            err=True,
        )
        return False
    elif not is_lockfile_hash_match(project, lockfile_file):
        project.core.ui.echo(
            "Lock file hash doesn't match pyproject.toml, packages may be outdated",
            style="yellow",
            err=True,
        )
        return False
    return True


def get_settings(project: Project):
    return project.pyproject.settings["plugin"]["torch"]


class InstallCommand(BaseCommand):
    name = "install"
    description = "Install torch packages from lockfile"

    def add_arguments(self, parser):
        parser.add_argument("api", help="the api to use, e.g. cuda version or rocm")

    def handle(self, project: Project, options: dict):
        plugin_config = Configuration.from_toml(get_settings(project))

        resolves = plugin_config.variants
        if options.api not in resolves:
            raise ValueError(
                f"unknown API {options.api}, expected one of {[v for v in resolves]}"
            )

        lockfile = read_lockfile(project, plugin_config.lockfile)

        spec_for_version = lockfile[options.api]

        (source, local_version) = resolves[options.api]

        if is_pdm210:
            from pdm.project.lockfile import FLAG_STATIC_URLS  # pylint: disable=C0415

            class OverrideLockfile:
                def __init__(self, lockfile):
                    self._lockfile = lockfile

                @property
                def strategy(self):
                    strategies = self._lockfile.strategy
                    strategies.add(FLAG_STATIC_URLS)

                    return strategies

                def __getattr__(self, name):
                    return getattr(self._lockfile, name)

            original_lockfile = project.lockfile

            project._lockfile = OverrideLockfile(original_lockfile)  # pylint: disable=W0212

        reqs = [
            parse_requirement(f"{req}{local_version}", False)
            for req in plugin_config.dependencies
        ]

        do_sync(
            project,
            raw_sources=[
                {
                    "name": "torch",
                    "url": source,
                    "type": "index",
                    "verify_ssl": True,
                }
            ],
            requirements=reqs,
            lockfile=spec_for_version,
        )

        if is_pdm210:
            project._lockfile = original_lockfile  # pylint: disable=W0212


class LockCommand(BaseCommand):
    name = "lock"
    description = "Lock Torch and its dependencies to a specific version"

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            help="validate that the lockfile is up to date",
            action="store_true",
        )

    def handle(self, project: Project, options: dict):
        plugin_config = Configuration.from_toml(get_settings(project))

        if options.check:
            is_updated = check_lockfile(project, plugin_config.lockfile)
            if not is_updated:
                project.core.ui.echo(
                    "Lockfile is [error]out of date[/].",
                    err=True,
                    verbosity=Verbosity.DETAIL,
                )
                sys.exit(1)
            else:
                project.core.ui.echo(
                    "Lockfile is [success]up to date[/].",
                    err=True,
                    verbosity=Verbosity.DETAIL,
                )
                sys.exit(0)

        results = {}
        for api, (url, local_version) in plugin_config.variants.items():
            reqs = [
                parse_requirement(f"{req}{local_version}", False)
                for req in plugin_config.dependencies
            ]

            results[api] = do_lock(
                project,
                [
                    {
                        "name": "torch",
                        "url": url,
                        "type": "index",
                        "verify_ssl": True,
                    }
                ],
                requirements=reqs,
            )

        write_lockfile(project, plugin_config.lockfile, results)


class ExportCommand(BaseCommand):
    name = "export"
    description = "Export Torch and its dependencies for a specific version"

    def add_arguments(self, parser):
        parser.add_argument("api", help="the api to use, e.g. cuda version or rocm")
        PDMExportCommand.add_arguments(None, parser)

    def handle(self, project: Project, options: dict):
        plugin_config = Configuration.from_toml(get_settings(project))
        resolves = plugin_config.variants
        if options.api not in resolves:
            raise ValueError(
                f"unknown API {options.api}, expected one of {[v for v in resolves]}"
            )

        lockfile = read_lockfile(project, plugin_config.lockfile)
        spec_for_version = lockfile[options.api]

        (source, local_version) = resolves[options.api]

        if is_pdm210:
            from pdm.project.lockfile import FLAG_STATIC_URLS

            class OverrideLockfile:
                def __init__(self, lockfile):
                    self._lockfile = lockfile

                @property
                def strategy(self):
                    strategies = self._lockfile.strategy
                    strategies.add(FLAG_STATIC_URLS)

                    return strategies

                def __getattr__(self, name):
                    return getattr(self._lockfile, name)

            original_lockfile = project.lockfile
            project._lockfile = OverrideLockfile(original_lockfile)  # pylint: disable=W0212

        reqs = [
            parse_requirement(f"{req}{local_version}", False)
            for req in plugin_config.dependencies
        ]

        candidates = resolve_candidates_from_lockfile(
            project,
            reqs,
            [
                {
                    "name": "torch",
                    "url": source,
                    "type": "index",
                    "verify_ssl": True,
                }
            ],
            spec_for_version,
            for_install=False,
        )
        packages = (
            candidate for candidate in candidates.values() if not candidate.req.extras
        )

        if is_pdm210:
            project._lockfile = original_lockfile  # pylint: disable=W0212

        content = FORMATS[options.format].export(project, packages, options)
        if options.output:
            Path(options.output).write_text(content, encoding="utf-8")
        else:
            # Use a regular print to avoid any formatting / wrapping.
            print(content)


class TorchCommand(BaseCommand):
    """Generate a lockfile for torch specifically."""

    name = "torch"
    description = "Manage torch dependencies"
    parser = None

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(
            title="Sub commands", help="sub-command help", dest="command"
        )
        LockCommand.register_to(subparsers)
        InstallCommand.register_to(subparsers)
        ExportCommand.register_to(subparsers)

        self.parser = parser

    def handle(self, project: Project, options) -> None:
        self.parser.print_help()


def torch_plugin(core: Core):
    if is_pdm28 and not is_pdm29:
        raise RuntimeError(
            "pdm 2.8.* is not supported due to not https://github.com/pdm-project/pdm/issues/2151"
        )
    core.register_command(TorchCommand, "torch")
