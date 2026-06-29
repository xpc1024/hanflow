def test_package_importable():
    import hanflow

    assert hanflow.__version__ == "0.1.0"
