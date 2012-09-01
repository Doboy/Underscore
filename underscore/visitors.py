import ast
import base

from also import also

class ConstantFinder(ast.NodeTransformer):
    """Rename all constants and takes a note of it, so that
    in the final phase we can inject an assignment node that 
    declares them. 
    """
    def __init__(self, env):
        self.env = env
        self._assignmentManager = base.AssignmentManager()

    def __nonzero__(self):
        return bool(self._assignmentManager)

    def visit_Num(self, node):
        return self.addConstant(node, node.n)

    def visit_Str(self, node):
        return self.addConstant(node, node.s)

    def addConstant(self, node, value):
        delc = self.env.generateNextDeclaration()
        self._assignmentManager.addAssignment(delc.name, node)

    def assignNode(self):
        return self._assignmentManager.assignNode()

class Declarer(base.BaseVisitor):

    def visit_arguments(self, node):
        for arg in node.args:
            if isinstance(arg.ctx, ast.Param):
                self.declare(arg.id)

    def visit_Assign(self, node):
        for target in node.targets:
            self.generic_declare(target)
        ast.NodeVisitor.generic_visit(self, node)

    @also('visit_FunctionDef')
    def visit_ClassDef(self, node):
        self.declare(node.name)
        with self.extendFrame(node):
            self.visit_queue.append(node)

    @also('visit_ImportFrom')
    def visit_Import(self, node):
        for alias in node.names:
            if alias.asname is None:
                alias.asname = alias.name
            self.declare(alias.asname)

    def visit_For(self, node):
        self.generic_declare(node.target)
        ast.NodeVisitor.generic_visit(self, node)

    def visit_FunctionDef(self, node):
        self.declare(node.name)
        with self.extendFrame(node):
            for arg in node.args.args:
                self.generic_declare(arg)
            self.visit_queue.append(node)

    def visit_Global(self, node):
        for name in node.names:
            self.declare(name, _global=True)

    def generic_declare(self, target):
        specific_declare = 'declare_' + type(target).__name__
        getattr(self, specific_declare)(target)

    def declare(self, name, _global=False):
        assert isinstance(name, str), name
        self._current_frame.add(name, _global)

    def declare_Name(self, node):
        self.declare(node.id)

    def declare_Subscript(self, node):
        ast.NodeVisitor.generic_visit(self, node)

    @also('declare_List')
    def declare_Tuple(self, node):
        for element in node.elts:
            self.generic_declare(element)
