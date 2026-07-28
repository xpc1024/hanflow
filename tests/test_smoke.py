def test_package_importable():
    """Package imports and its __version__ matches pyproject.toml.

    Reads the version from pyproject.toml (the authoritative source) so this
    test never breaks on a version bump.
    """
    import tomllib
    from pathlib import Path

    import hanflow

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as fh:
        expected = tomllib.load(fh)["project"]["version"]
    assert hanflow.__version__ == expected
