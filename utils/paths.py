"""应用目录和相对路径解析的单一来源。"""

from dataclasses import dataclass
from pathlib import Path

PathLike = str | Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_project_path(path: PathLike) -> Path:
    """将用户路径展开并相对于项目根目录解析。"""
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = PROJECT_ROOT / resolved
    return resolved.resolve()


@dataclass(frozen=True)
class AppPaths:
    """应用标准目录。"""

    root: Path = PROJECT_ROOT

    @property
    def configs(self) -> Path:
        return self.root / "configs"

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def loras(self) -> Path:
        return self.root / "loras"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def outputs(self) -> Path:
        return self.root / "outputs"

    @property
    def history(self) -> Path:
        return self.outputs / "history"

    @property
    def logs(self) -> Path:
        return self.root / "logs"


APP_PATHS = AppPaths()
