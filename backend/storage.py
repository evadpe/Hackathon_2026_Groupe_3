import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class StorageBackend(ABC):
    kind: str

    @abstractmethod
    def write_bytes(self, relative_path: str, data: bytes) -> str:
        raise NotImplementedError

    @abstractmethod
    def read_bytes(self, relative_path: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_files(self, relative_dir: str, suffix: str | None = None) -> list[str]:
        raise NotImplementedError

    def write_json(self, relative_path: str, payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        return self.write_bytes(relative_path, encoded)

    def read_json(self, relative_path: str) -> dict[str, Any]:
        return json.loads(self.read_bytes(relative_path).decode("utf-8"))

    @staticmethod
    def normalize(relative_path: str) -> str:
        return relative_path.strip("/")


class LocalStorage(StorageBackend):
    kind = "local"

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _full_path(self, relative_path: str) -> Path:
        return self.base_dir / self.normalize(relative_path)

    def write_bytes(self, relative_path: str, data: bytes) -> str:
        full_path = self._full_path(relative_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        return self.normalize(relative_path)

    def read_bytes(self, relative_path: str) -> bytes:
        return self._full_path(relative_path).read_bytes()

    def exists(self, relative_path: str) -> bool:
        return self._full_path(relative_path).exists()

    def list_files(self, relative_dir: str, suffix: str | None = None) -> list[str]:
        target_dir = self._full_path(relative_dir)
        if not target_dir.exists():
            return []

        files = [path for path in target_dir.iterdir() if path.is_file()]
        if suffix:
            files = [path for path in files if path.name.endswith(suffix)]

        return sorted(
            str(path.relative_to(self.base_dir)).replace("\\", "/")
            for path in files
        )


class HdfsStorage(StorageBackend):
    kind = "hdfs"

    def __init__(self, url: str, user: str, base_path: str):
        try:
            from hdfs import InsecureClient
        except ImportError as exc:
            raise RuntimeError(
                "Le backend HDFS nécessite le package 'hdfs'."
            ) from exc

        self.base_path = base_path.rstrip("/")
        self.client = InsecureClient(url=url, user=user)
        self._ensure_dir("")

    def _absolute_path(self, relative_path: str) -> str:
        relative_path = self.normalize(relative_path)
        if not relative_path:
            return self.base_path
        return f"{self.base_path}/{relative_path}"

    def _ensure_dir(self, relative_dir: str) -> None:
        self.client.makedirs(self._absolute_path(relative_dir))

    def write_bytes(self, relative_path: str, data: bytes) -> str:
        relative_path = self.normalize(relative_path)
        parent_dir = str(Path(relative_path).parent).replace("\\", "/")
        if parent_dir != ".":
            self._ensure_dir(parent_dir)

        with self.client.write(self._absolute_path(relative_path), overwrite=True) as writer:
            writer.write(data)

        return relative_path

    def read_bytes(self, relative_path: str) -> bytes:
        with self.client.read(self._absolute_path(relative_path)) as reader:
            return reader.read()

    def exists(self, relative_path: str) -> bool:
        return self.client.status(self._absolute_path(relative_path), strict=False) is not None

    def list_files(self, relative_dir: str, suffix: str | None = None) -> list[str]:
        relative_dir = self.normalize(relative_dir)
        directory_status = self.client.status(self._absolute_path(relative_dir), strict=False)
        if directory_status is None:
            return []

        file_names = self.client.list(self._absolute_path(relative_dir))
        paths = []
        for name in file_names:
            relative_path = "/".join(part for part in [relative_dir, name] if part)
            status = self.client.status(self._absolute_path(relative_path), strict=False)
            if status and status.get("type") == "FILE":
                if suffix is None or relative_path.endswith(suffix):
                    paths.append(relative_path)
        return sorted(paths)


def get_storage() -> StorageBackend:
    backend = os.getenv("STORAGE_BACKEND", "local").strip().lower()
    if backend == "hdfs":
        return HdfsStorage(
            url=os.getenv("HDFS_URL", "http://namenode:9870"),
            user=os.getenv("HDFS_USER", "hdfs"),
            base_path=os.getenv("HDFS_BASE_PATH", "/stepahead-lake"),
        )

    return LocalStorage(
        base_dir=os.getenv("DATA_LAKE_BASE_DIR", str(Path(__file__).parent / "data_lake"))
    )
