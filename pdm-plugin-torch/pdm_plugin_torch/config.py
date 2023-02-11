from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Configuration:
    dependencies: list[str]
    enable_cpu: bool = False

    enable_cuda: bool = False
    cuda_versions: list[str] = field(default_factory=list)

    enable_rocm: bool = False
    rocm_versions: list[str] = field(default_factory=list)

    lockfile: str = "torch.lock"

    def from_toml(data: dict[str, str | list[str] | bool]) -> "Configuration":
        fixed_dashes = {k.replace("-", "_"): v for (k, v) in data.items()}

        return Configuration(**fixed_dashes)

    @property
    def variants(self):
        resolves = {}

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

        if self.enable_cpu:
            resolves["cpu"] = ("https://download.pytorch.org/whl/cpu", "")

        return resolves
