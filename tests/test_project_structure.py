def test_layer_packages_are_importable():
    import application  # noqa: F401
    import domain  # noqa: F401
    import infrastructure  # noqa: F401
    from interface import http  # noqa: F401
