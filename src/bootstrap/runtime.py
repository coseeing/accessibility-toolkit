import logging
from pathlib import Path
import sys


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _macos_app_support_dir(app_name: str) -> Path:
    return Path.home() / "Library" / "Application Support" / app_name


def _macos_logs_dir(app_name: str) -> Path:
    return Path.home() / "Library" / "Logs" / app_name


def default_log_path(app_name: str = "nvda-remote-client") -> Path:
    if _is_frozen():
        if sys.platform == "darwin":
            return _macos_logs_dir(app_name) / f"{app_name}.log"
        return Path(sys.executable).resolve().parent / f"{app_name}.log"
    return Path.cwd().resolve() / f"{app_name}.log"


def default_config_path(app_name: str = "nvda-remote-client") -> Path:
    if _is_frozen():
        if sys.platform == "darwin":
            return _macos_app_support_dir(app_name) / f"{app_name}.json"
        return Path(sys.executable).resolve().parent / f"{app_name}.json"
    return Path.cwd().resolve() / f"{app_name}.json"


def configure_logging(
    log_path: Path | None = None,
    app_name: str = "nvda-remote-client",
) -> Path:
    if log_path is None:
        log_path = default_log_path(app_name)
    log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    root_logger = logging.getLogger()
    try:
        if not root_logger.handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format=log_format,
                filename=log_path,
                filemode="a",
            )
        else:
            file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(file_handler)
        logging.getLogger(__name__).info("Logging initialized at %s", log_path)
    except OSError as error:
        if not root_logger.handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format=log_format,
            )
        logging.getLogger(__name__).warning(
            "File logging unavailable at %s: %s",
            log_path,
            error,
        )
    return log_path
