import unittest

from intellic.dialects import affine, arith, builtin, scf
from intellic.ir.parser import parse_operation
from intellic.ir.syntax import (
    Attribute,
    Block,
    Builder,
    Operation,
    Region,
    Type,
    VerificationError,
    i1,
    i32,
    verify_operation,
)
from intellic.ir.syntax.printer import print_operation


def operation_names(op):
    names = [op.name]
    for region in op.regions:
        for block in region.blocks:
            for child in block.operations:
                names.extend(operation_names(child))
    return names


class ScfVerificationTests(unittest.TestCase):
    def test_verify_rejects_malformed_parsed_scf_if(self) -> None:
        text = """
        "builtin.module"() ({
          %0 = "arith.constant"() {'value': 0} : () -> (index)
          "scf.if"(%0) ({
            "scf.condition"(%0) : () -> ()
          }) : () -> ()
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.if"):
            verify_operation(parsed)

    def test_verify_rejects_scf_condition_outside_while_before_region(self) -> None:
        text = """
        "builtin.module"() ({
          %0 = "arith.constant"() {'value': 1} : () -> (i1)
          "scf.condition"(%0) : () -> ()
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.condition"):
            verify_operation(parsed)

    def test_verify_rejects_scf_reduce_return_outside_reduce_region(self) -> None:
        text = """
        "builtin.module"() ({
          %0 = "arith.constant"() {'value': 1} : () -> (i32)
          "scf.reduce.return"(%0) : () -> ()
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.reduce.return"):
            verify_operation(parsed)

    def test_verify_rejects_non_terminal_scf_yield(self) -> None:
        text = """
        "builtin.module"() ({
          "scf.yield"() : () -> ()
          %0 = "arith.constant"() {'value': 1} : () -> (i32)
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.yield"):
            verify_operation(parsed)

    def test_verify_rejects_standalone_scf_forall_in_parallel(self) -> None:
        text = """
        "builtin.module"() ({
          "scf.forall.in_parallel"() {'yield_count': 0} : () -> ()
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.forall.in_parallel"):
            verify_operation(parsed)

    def test_verify_rejects_standalone_scf_reduce(self) -> None:
        text = """
        "builtin.module"() ({
          "scf.reduce"() {'operand_count': 0} : () -> ()
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.reduce"):
            verify_operation(parsed)

    def test_verify_rejects_non_terminal_scf_reduce(self) -> None:
        text = """
        "builtin.module"() ({
          "scf.reduce"() {'operand_count': 0} : () -> ()
          %0 = "arith.constant"() {'value': 1} : () -> (i32)
        }) : () -> ()
        """

        parsed = parse_operation(text)

        with self.assertRaisesRegex(VerificationError, "scf.reduce"):
            verify_operation(parsed)


if __name__ == "__main__":
    unittest.main()
