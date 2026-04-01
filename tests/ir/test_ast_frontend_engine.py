from __future__ import annotations

import ast

from htp.ir.frontends import ASTFrontendVisitor, handles, load_function_ast


class DemoASTVisitor(ASTFrontendVisitor):
    @handles(ast.FunctionDef, decorator="worker")
    def build_worker(self, node, context):
        return ("function", node.name, context.entry)

    @handles(ast.Expr, call="emit")
    def build_emit(self, node, context):
        return ("expr", self.call_name(node), context.entry)


def test_ast_frontend_dispatch_matches_decorator_and_call_handlers() -> None:
    def demo_surface():
        @surface.worker(role="producer")
        def worker():
            surface.emit("tile")

    function_ast = load_function_ast(demo_surface)
    visitor = DemoASTVisitor()
    context = visitor.build_context(
        frontend_id="demo.frontend",
        dialect_id="demo",
        function_ast=function_ast,
        kernel_spec=None,
        target={},
        entry="demo_surface",
    )

    worker_node = next(node for node in function_ast.root.body if isinstance(node, ast.FunctionDef))
    emit_node = next(node for node in worker_node.body if isinstance(node, ast.Expr))

    assert visitor.dispatch(worker_node, context) == ("function", "worker", "demo_surface")
    assert visitor.dispatch(emit_node, context) == ("expr", "emit", "demo_surface")
