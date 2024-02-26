"""Plugin configuration."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Configuration:
    """
    Plugin configuration.

    Attributes:
        dependencies: list of top level dependencies.
        enable_cpu: CPU feature flag.
        enable_cuda: CUDA feature flag.
        enable_rocm: ROCm feature flag.
        cuda_versions: list of versions for CUDA to support.
        rocm_versions: list of ROCm versions to support.
        lockfile: path to the lock file to use.
    """

    # Dependency list.
    dependencies: list[str]
    # Feature flags.
    enable_cpu: bool = False
    enable_cuda: bool = False
    enable_rocm: bool = False
    # Version identifiers for the different possible versioned dependencies.
    cuda_versions: list[str] = field(default_factory=list)
    rocm_versions: list[str] = field(default_factory=list)
    # Lockfile configuration.
    lockfile: str = "torch.lock"

    @staticmethod
    def from_toml(data: dict[str, str | list[str] | bool]) -> "Configuration":
        """
        Create a configuration object from a pyproject.toml configuration file.

        Args:
            data: parsed TOML of the pyproject file.

        Returns:
            Configuration object.
        """
        fixed_dashes = {k.replace("-", "_"): v for (k, v) in data.items()}

        return Configuration(**fixed_dashes)

    @property
    def variants(self) -> dict[str, tuple[str, str]]:
        """
        Get resolution URL and build identifier for all configured variants for the plugin.

        Returns:
            A dictionary of torch build alternatives to a tuple of
            (resolution URL, build identifier).
        """
        resolves = {}
        if self.enable_cpu:
            # We can omit the build identifier for the CPU only versions
            # since the resolution at the CPU URL works correctly for all
            # versions only without a tag (see the MacOS builds at
            # https://download.pytorch.org/whl/cpu).
            resolves["cpu"] = ("https://download.pytorch.org/whl/cpu", "")
        if self.enable_cuda:
            for cuda_version in self.cuda_versions:
                resolves[cuda_version] = (
                    f"https://download.pytorch.org/whl/{cuda_version}/",
                    f"+{cuda_version}",
                )
        if self.enable_rocm:
            for rocm_version in self.rocm_versions:
                resolves[f"rocm{rocm_version}"] = (
                    "https://download.pytorch.org/whl/",
                    f"+rocm{rocm_version}",
                )
        return resolves
