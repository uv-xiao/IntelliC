import unittest


class ImportTests(unittest.TestCase):
    def test_package_import_exposes_nonempty_version(self) -> None:
        import intellic

        self.assertIsInstance(intellic.__version__, str)
        self.assertTrue(intellic.__version__)

    def test_core_namespace_imports_without_side_effects(self) -> None:
        import intellic.ir

        self.assertEqual(intellic.ir.__all__, ())


if __name__ == "__main__":
    unittest.main()
