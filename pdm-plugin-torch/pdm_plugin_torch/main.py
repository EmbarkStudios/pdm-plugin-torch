from __future__ import annotations

import sys

from typing import Iterable

import tomlkit

from pdm import termui
from pdm._types import RepositoryConfig
from pdm.cli.commands.base import BaseCommand
from pdm.cli.utils import fetch_hashes, format_lockfile, format_resolution_impossible
from pdm.core import Core
from pdm.models.candidates import Candidate
from pdm.models.repositories import BaseRepository, LockedRepository
from pdm.models.requirements import Requirement, parse_requirement
from pdm.models.specifiers import get_specifier
from pdm.project import Project
from pdm.resolver import resolve
from pdm.resolver.providers import BaseProvider
from pdm.termui import Verbosity
from pdm.utils import atomic_open_for_write, expand_env_vars_in_auth
from resolvelib.reporters import BaseReporter
from resolvelib.resolvers import ResolutionImpossible, ResolutionTooDeep, Resolver

from pdm_plugin_torch.config import Configuration


def sources(project: Project, sources: list) -> list[RepositoryConfig]:
    result: dict[str, RepositoryConfig] = {}
    for source in project.pyproject.settings.get("source", []):
        result[source["name"]] = RepositoryConfig(**source, config_prefix="pypi")

    for source in sources:
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
    """Build a provider class for resolver.
    :param strategy: the resolve strategy
    :param tracked_names: the names of packages that needs to update
    :param for_install: if the provider is for install
    :returns: The provider object
    """
    from pdm.models.requirements import strip_extras
    from pdm.resolver.providers import (
        BaseProvider,
        EagerUpdateProvider,
        ReusePinProvider,
    )
    from pdm.utils import normalize_name

    repository = get_repository(
        project, raw_sources, for_install=for_install, lockfile=lockfile
    )

    overrides = {
        normalize_name(k): v for k, v in project.pyproject.resolution_overrides.items()
    }

    locked_repository: LockedRepository | None = None
    if strategy != "all" or for_install:
        try:
            locked_repository = LockedRepository(lockfile, sources, project.environment)
        except Exception:
            if for_install:
                raise
            project.core.ui.echo(
                "Unable to reuse the lock file as it is not compatible with PDM",
                style="warning",
                err=True,
            )

    if locked_repository is None:
        return BaseProvider(repository, allow_prereleases, overrides)

    if for_install:
        return BaseProvider(locked_repository, allow_prereleases, overrides)

    provider_class = ReusePinProvider if strategy == "reuse" else EagerUpdateProvider
    tracked_names = [strip_extras(name)[0] for name in tracked_names or ()]

    return provider_class(
        locked_repository.all_candidates,
        tracked_names,
        repository,
        allow_prereleases,
        overrides,
    )


def get_repository(
    project: Project,
    raw_sources: list,
    cls: type[BaseRepository] | None = None,
    for_install: bool = False,
    lockfile: dict = None,
) -> BaseRepository:
    """Get the repository object"""
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
            data = format_lockfile(project, mapping, dependencies)
            ui.echo(f"{termui.Emoji.LOCK} Lock successful")
            return data


def write_lockfile(
    project: Project, lock_name: str, toml_data: dict, show_message: bool = True
) -> None:
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
                project, raw_sources, for_install=True, lockfile=lockfile
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
        reinstall=True,
        only_keep=False,
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
    return project.pyproject.settings["plugins"]["torch"]


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


class TorchCommand(BaseCommand):
    """Generate a lockfile for torch specifically."""

    name = "torch"
    description = "Manage torch dependencies"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(
            title="Sub commands", help="sub-command help", dest="command"
        )

        LockCommand.register_to(subparsers)
        InstallCommand.register_to(subparsers)

        self.parser = parser

    def handle(self, project: Project, options) -> None:
        self.parser.print_help()


def torch_plugin(core: Core):
    core.register_command(TorchCommand, "torch")
