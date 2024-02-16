# Copyright (C) 2024 qBraid
#
# This file is part of the qBraid-SDK
#
# The qBraid-SDK is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the qBraid-SDK, as per Section 15 of the GPL v3.
"""
Module for serving system information.

"""
import logging
import os
import re
import site
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import List, Optional, Tuple

import requests

from qbraid._qdevice import QDEVICE_LIBS
from qbraid.exceptions import QbraidError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_python_version_from_exe(venv_path: Path) -> str:
    """
    Gets the Python version used in the specified virtual environment by executing
    the Python binary within the venv's bin (or Scripts) directory.

    Args:
        venv_path (Path): The path to the virtual environment directory.

    Returns:
        A string representing the Python version (e.g., '3.11.7'), or None if an error occurs.
    """
    # Adjust the path to the Python executable depending on the operating system
    python_executable = venv_path / ("Scripts" if sys.platform == "win32" else "bin") / "python"

    try:
        # Run the Python executable with '--version' and capture the output
        result = subprocess.run(
            [str(python_executable), "--version"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Python version info could be in stdout or stderr
        version_output = result.stdout or result.stderr

        # Python 3.11.7 --> 3.11.7
        return version_output.split()[1]

    except subprocess.CalledProcessError as e:
        logger.warning("An error occurred while trying to get the Python version: %s", e)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("Unexpected error: %s", e)

    return None


def get_python_version_from_cfg(venv_path: Path) -> str:
    """
    Reads a pyvenv.cfg file within a given virtual environment directory and extracts
    the major and minor Python version.

    Args:
        venv_path (pathlib.Path): The path to the virtual environment directory.

    Returns:
        A string representing the Python version (e.g., '3.11.7'), or None if
        the version cannot be determined or the pyvenv.cfg file does not exist.
    """
    pyvenv_cfg_path = venv_path / "pyvenv.cfg"
    if not pyvenv_cfg_path.exists():
        logger.warning("pyvenv.cfg file not found in the virtual environment: %s", venv_path)
        return None

    try:
        with pyvenv_cfg_path.open("r") as file:
            for line in file:
                if line.startswith("version ="):
                    version_full = line.strip().split("=")[1].strip()
                    version_parts = version_full.split(".")
                    return f"{version_parts[0]}.{version_parts[1]}"
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("An error occurred while reading %s: %s", pyvenv_cfg_path, e)

    return None


def get_venv_site_packages_path(venv_path: Path) -> Path:
    """
    Determines the site-packages directory for a given virtual environment in an OS-agnostic manner.
    Automatically selects the Python version if a single version is present in the 'lib' directory.
    If multiple versions are detected, it attempts to determine the correct version through
    configuration files or the Python executable.

    Args:
        venv_path (pathlib.Path): The path to the virtual environment directory.

    Returns:
        A Path object pointing to the site-packages directory, or None if unable to determine.

    Raises:
        QbraidError: If an error occurs while determining the site-packages path.
    """
    if sys.platform == "win32":
        return venv_path / "Lib" / "site-packages"

    python_dirs = sorted(venv_path.glob("lib/python*"))
    if not python_dirs:
        raise QbraidError("No Python directories found in the virtual environment.")

    if len(python_dirs) == 1:
        return python_dirs[0] / "site-packages"

    python_version = get_python_version_from_cfg(venv_path) or get_python_version_from_exe(
        venv_path
    )
    if not python_version:
        raise QbraidError("Unable to determine Python version from the virtual environment.")

    major_minor_version = ".".join(python_version.split(".")[:2])
    lib_python_dir = venv_path / f"lib/python{major_minor_version}"
    return lib_python_dir / "site-packages"


def get_active_site_packages_path() -> str:
    """Retrieves the site-packages path of the current Python environment."""

    # List of all site-packages directories
    site_packages_paths = site.getsitepackages()

    if len(site_packages_paths) == 1:
        return site_packages_paths[0]

    # Path to the currently running Python interpreter
    python_executable_path = sys.executable

    # Base path of the Python environment
    env_base_path = os.path.dirname(os.path.dirname(python_executable_path))

    # Find the site-packages path that is within the same environment
    for path in site_packages_paths:
        if env_base_path in path:
            return path

    raise QbraidError("Failed to find site-packages path.")


def get_latest_package_version(package: str) -> str:
    """Retrieves the latest version of package from PyPI."""
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data["info"]["version"]
    except requests.RequestException as err:
        raise QbraidError(f"Failed to retrieve latest {package} version from PyPI.") from err


def get_local_package_version(package: str) -> str:
    """Retrieves the local version of a package."""
    try:
        return version(package)
    except PackageNotFoundError as err:
        raise QbraidError(f"{package} is not installed in the current environment.") from err


def get_local_package_path(package: str) -> str:
    """Retrieves the local path of a package."""
    try:
        site_packages_path = get_active_site_packages_path()
        return os.path.join(site_packages_path, package)
    except PackageNotFoundError as err:
        raise QbraidError(f"{package} is not installed in the current environment.") from err


def get_qbraid_envs_paths() -> List[Path]:
    """
    Returns a list of paths to qBraid environments.

    If the QBRAID_ENVS_PATH environment variable is set, it splits the variable by ':' to
    accommodate multiple paths. If QBRAID_ENVS_PATH is not set, returns a list containing
    the default qBraid environments path (~/.qbraid/environments).

    Returns:
        A list of pathlib.Path objects representing the qBraid environments paths.
    """
    qbraid_envs_path = os.getenv("QBRAID_ENVS_PATH")
    if qbraid_envs_path is not None:
        return [Path(path) for path in qbraid_envs_path.split(":")]
    return [Path.home() / ".qbraid" / "environments"]


def is_valid_slug(slug: str) -> bool:
    """Returns True if the slug is valid, False otherwise."""
    if len(slug) > 20:
        return False

    alphanumeric_part = slug[-6:]
    if not re.match(r"^[a-zA-Z0-9]{6}$", alphanumeric_part):
        return False

    if slug[-7:-6] != "_":
        return False

    remaining_part = slug[:-7]
    if not re.match(r"^[a-z0-9_]*$", remaining_part):
        return False

    return True


def check_proxy(proxy_spec: Tuple[str, ...], slug_path: Optional[Path] = None) -> Tuple[bool, bool]:
    """
    Checks if the specified proxy file exists and contains the string 'qbraid'.

    Args:
        proxy_spec (Tuple[str, ...]): A tuple specifying the path components from 'site-packages'
                                      to the target proxy file, e.g. ("botocore", "httpsession.py").
        slug_path (optional, Path): The base path to prepend to the 'pyenv' directory.

    Returns:
        A tuple of two booleans: The first indicates whether the specified proxy file exists;
        the second, if the file exists, is True if it contains 'qbraid', False otherwise.
    """
    try:
        if slug_path is None:
            site_packages: str = get_active_site_packages_path()
            site_packages_path = Path(site_packages)
        else:
            site_packages_path = get_venv_site_packages_path(slug_path / "pyenv")
    except QbraidError as err:
        logger.debug(err)
        return False, False

    target_file_path = site_packages_path.joinpath(*proxy_spec)

    if not target_file_path.exists():
        return False, False

    try:
        with target_file_path.open("r", encoding="utf-8") as file:
            for line in file:
                if "qbraid" in line:
                    return True, True
        return True, False
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.debug("Unexpected error checking qBraid proxy: %s", e)

    return True, False


def qbraid_jobs_state(device_lib: str) -> Tuple[bool, bool]:
    """Checks if qBraid Quantum Jobs are supported and if so, checks whether they are enabled.

    Args:
        device_lib (str): The name of the quantum device library, e.g., "braket".

    Returns:
        A tuple of two booleans: The first indicates whether the specified proxy file exists;
        the second, if the file exists, is True if it contains 'qbraid', False otherwise.
    """
    if device_lib not in QDEVICE_LIBS:
        return False, False

    if device_lib == "braket":
        proxy_spec = ("botocore", "httpsession.py")
    else:
        return False, False

    return check_proxy(proxy_spec)
