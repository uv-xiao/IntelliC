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


class DiagnosticsTests(unittest.TestCase):
    def test_parser_rejects_unknown_custom_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected operation"):
            parse_operation("not-an-operation")

    def test_parser_rejects_unknown_value_use(self) -> None:
        text = '%0 = "arith.addi"(%missing, %missing) : () -> (i32)'

        with self.assertRaisesRegex(ValueError, "unknown SSA value"):
            parse_operation(text)

    def test_parser_rejects_parent_use_of_region_local_value(self) -> None:
        text = """
        "test.parent"(%0) ({
          %0 = "arith.constant"() <{value = 1}> : () -> i32
        }) : () -> ()
        """

        with self.assertRaisesRegex(ValueError, "unknown SSA value"):
            parse_operation(text)

    def test_printer_rejects_unsupported_property_values(self) -> None:
        op = Operation.create("test.unsupported", properties={"payload": object()})

        with self.assertRaisesRegex(TypeError, "unsupported property"):
            print_operation(op)


if __name__ == "__main__":
    unittest.main()
