"""Script to bump the project version, and update the lock file.

This script increments the specified part (major, minor, or patch) of the version,
updates the relevant files, and runs 'uv lock' to update dependencies.
"""

import argparse
import json
import logging
import re
import subprocess
import sys
import tomllib
from pathlib import Path

logger = logging.getLogger(__name__)

# Determine the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
MANIFEST_PATH = (
    PROJECT_ROOT
    / "custom_components"
    / "northern_powergrid_power_cuts"
    / "manifest.json"
)


def get_current_version_pyproject():
    """Read the current version from pyproject.toml."""
    try:
        with PYPROJECT_PATH.open("rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except FileNotFoundError:
        logger.exception("%s not found.", PYPROJECT_PATH)
        sys.exit(1)
    except KeyError:
        logger.exception(
            "Could not find 'version' under '[project]' in %s.", PYPROJECT_PATH
        )
        sys.exit(1)
    except Exception:
        logger.exception("Error reading %s", PYPROJECT_PATH)
        sys.exit(1)


def update_pyproject_toml(new_version):
    """Update the version in pyproject.toml."""
    try:
        with PYPROJECT_PATH.open(encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        logger.exception("%s not found for updating.", PYPROJECT_PATH)
        sys.exit(1)
    except Exception:
        logger.exception("Error reading %s for update.", PYPROJECT_PATH)
        sys.exit(1)

    new_lines = []
    in_project_section = False
    updated = False
    for line in lines:
        stripped_line = line.strip()
        if stripped_line == "[project]":
            in_project_section = True
            new_lines.append(line)
        elif in_project_section and stripped_line.startswith("version"):
            # Match 'version = "..."'
            if re.match(r'^\s*version\s*=\s*".*"\s*$', line):
                indent = line[: line.find("version")]  # Preserve original indentation
                new_lines.append(f'{indent}version = "{new_version}"\n')
                updated = True
                # Assume version is unique in [project]; stop checking for this section
                # but continue processing lines for other sections.
                # To be extremely robust, one might continue 'in_project_section = True'
                # and ensure no other 'version =' lines are modified,
                # but this is usually sufficient.
            else:
                new_lines.append(line)  # Not the version assignment line
        elif stripped_line.startswith("[") and in_project_section:
            in_project_section = False  # Exited [project] section
            new_lines.append(line)
        else:
            new_lines.append(line)

    if not updated:
        logger.error(
            "Could not find 'version = \"...\"' line under [project] in %s.",
            PYPROJECT_PATH,
        )
        sys.exit(1)

    try:
        with PYPROJECT_PATH.open("w", encoding="utf-8") as f:
            f.writelines(new_lines)
        logger.info("Updated %s to version %s", PYPROJECT_PATH, new_version)
    except Exception:
        logger.exception("Error writing to %s", PYPROJECT_PATH)
        sys.exit(1)


def update_manifest_json(new_version):
    """Update the version in manifest.json."""
    try:
        with MANIFEST_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.exception("%s not found.", MANIFEST_PATH)
        sys.exit(1)
    except json.JSONDecodeError:
        logger.exception("Error decoding JSON from %s", MANIFEST_PATH)
        sys.exit(1)
    except Exception:
        logger.exception("Error reading %s", MANIFEST_PATH)
        sys.exit(1)
    data["version"] = new_version

    try:
        with MANIFEST_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")  # Add trailing newline for consistency
        logger.info("Updated %s to version %s", MANIFEST_PATH, new_version)
    except Exception:
        logger.exception("Error writing to %s", MANIFEST_PATH)
        sys.exit(1)


def bump_version_part(version_str, part_to_bump):
    """Increments the specified part of a version string X.Y.Z."""
    try:
        major, minor, patch = map(int, version_str.split("."))
    except ValueError as e:
        msg = f"Version string '{version_str}' is not in X.Y.Z format."
        raise ValueError(msg) from e

    if part_to_bump == "major":
        major += 1
        minor = 0
        patch = 0
    elif part_to_bump == "minor":
        minor += 1
        patch = 0
    elif part_to_bump == "patch":
        patch += 1
    else:
        # This case should ideally be caught by argparse choices
        msg = "Invalid part to bump. Must be 'major', 'minor', or 'patch'."
        raise ValueError(msg)

    return f"{major}.{minor}.{patch}"


def main():
    """Parse arguments, bump the version, update files, and run 'uv lock'."""
    parser = argparse.ArgumentParser(
        description="Bump the project version and update lock file."
    )
    parser.add_argument(
        "part",
        choices=["major", "minor", "patch"],
        help="The part of the version to bump (major, minor, or patch).",
    )
    args = parser.parse_args()

    current_version_pyproject = get_current_version_pyproject()
    logger.info("Current version (from pyproject.toml): %s", current_version_pyproject)
    try:
        new_version = bump_version_part(current_version_pyproject, args.part)
    except ValueError:
        logger.exception("Error occurred while bumping version")
        sys.exit(1)
    logger.info(
        "Bumping %s version from %s to %s...",
        args.part,
        current_version_pyproject,
        new_version,
    )
    update_pyproject_toml(new_version)
    update_manifest_json(new_version)

    logger.info("Running 'uv lock'...")
    try:
        process = subprocess.run(  # noqa: S603
            ["uv", "lock"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            cwd=PROJECT_ROOT,
            encoding="utf-8",
        )
        logger.info("uv lock successful.")
        if process.stdout:
            logger.info("uv lock output:\n%s", process.stdout.strip())
        # stderr from uv lock might not always be an error, could be progress
        if process.stderr:
            logger.warning("uv lock stderr output:\n%s", process.stderr.strip())

    except subprocess.CalledProcessError as e:
        logger.exception(
            "Error running 'uv lock': Command exited with status %s", e.returncode
        )
        if e.stdout:
            logger.exception("stdout:\n%s", e.stdout.strip())
        if e.stderr:
            logger.exception("stderr:\n%s", e.stderr.strip())
        sys.exit(1)
    except FileNotFoundError:
        logger.exception(
            "Error: 'uv' command not found. Make sure it is installed and in your PATH."
        )
        sys.exit(1)
    except Exception:
        logger.exception("An unexpected error occurred while running 'uv lock'")
        sys.exit(1)

    logger.info("Version bumped to %s and uv.lock updated successfully.", new_version)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
