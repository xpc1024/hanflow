def test_package_importable():
    import hanflow

    # Version is non-empty and parseable; not pinned to a literal so this test
    # doesn't rot on every release.
    assert hanflow.__version__
    assert isinstance(hanflow.__version__, str)
    assert len(hanflow.__version__.split(".")) >= 2
