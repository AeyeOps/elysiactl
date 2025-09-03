"""Elysia Control - Service management utility for Elysia AI and Weaviate."""

try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("elysiactl")
    except PackageNotFoundError:
        # Package is not installed, fallback to development version
        # This should only happen during development before installation
        __version__ = "0.0.0+dev"
except ImportError:
    # Python < 3.8, read from pyproject.toml as fallback
    try:
        from pathlib import Path

        import toml

        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path) as f:
                data = toml.load(f)
                __version__ = data.get("project", {}).get("version", "0.0.0+unknown")
        else:
            __version__ = "0.0.0+unknown"
    except:
        __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
