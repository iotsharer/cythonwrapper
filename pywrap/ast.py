import os
from .defaultconfig import Config
from .utils import indent_block, from_camel_case


class AstNode(object):
    def __init__(self):
        self.nodes = []

    def accept(self, exporter):
        for node in self.nodes:
            node.accept(exporter)
        method_name = "visit_" + from_camel_case(self.__class__.__name__)
        visit_method = getattr(exporter, method_name)
        visit_method(self)


class Ast(AstNode):
    """Abstract Syntax Tree."""
    def __init__(self):
        super(Ast, self).__init__()

    def __str__(self):
        result = "AST"
        if len(self.nodes) > 0:
            result += os.linesep + indent_block(os.linesep.join(
                [str(node) for node in self.nodes]), 1)
        return result


class Enum(AstNode):
    def __init__(self, filename, namespace, tipe):
        super(Enum, self).__init__()
        self.filename = filename
        self.namespace = namespace
        self.tipe = tipe
        self.constants = []

    def __str__(self):
        return "Enum '%s'" % self.tipe


class Typedef(AstNode):
    def __init__(self, filename, namespace, tipe, underlying_type):
        super(Typedef, self).__init__()
        self.filename = filename
        self.namespace = namespace
        self.tipe = tipe
        self.underlying_type = underlying_type

    def __str__(self):
        return "Typedef (%s) %s" % (self.underlying_type, self.tipe)


class Clazz(AstNode):
    def __init__(self, filename, namespace, name):
        super(Clazz, self).__init__()
        self.filename = filename
        self.namespace = namespace
        self.name = name

    def __str__(self):
        result = "%s '%s' ('%s')" % (
            self.__class__.__name__.replace("zz", "ss"),
            self.name, self.get_cppname())
        if self.namespace != "":
            result += " (namespace: '%s')" % self.namespace
        if len(self.nodes) > 0:
            result += os.linesep + indent_block(os.linesep.join(
                [str(node) for node in self.nodes]), 1)
        return result

    def get_cppname(self):
        return self.name

    def get_attached_typeinfo(self):
        return {}


class TemplateClazzSpecialization(Clazz):
    def __init__(self, filename, namespace, name, cppname, specialization):
        super(TemplateClazzSpecialization, self).__init__(
            filename, namespace, name)
        self.cppname = cppname
        self.specialization = specialization

    def get_cppname(self):
        return self.cppname

    def get_attached_typeinfo(self):
        return self.specialization


class FunctionBase(AstNode):
    def __init__(self, name):
        super(FunctionBase, self).__init__()
        self.name = name
        self.ignored = False

    def __str__(self):
        result = "%s '%s'" % (self.__class__.__name__, self.name)
        if len(self.nodes) > 0:
            result += os.linesep + indent_block(os.linesep.join(
                [str(arg) for arg in self.nodes]), 1)
        return result


class Function(FunctionBase):
    def __init__(self, filename, namespace, name, result_type):
        super(Function, self).__init__(name)
        self.filename = filename
        self.namespace = namespace
        self.result_type = result_type

    def __str__(self):
        result = super(Function, self).__str__()
        if self.result_type != "void":
            result += os.linesep + indent_block(
                "Returns (%s)" % self.result_type, 1)
        return result


class Constructor(FunctionBase):
    def __init__(self, class_name):
        super(Constructor, self).__init__("__init__")
        self.class_name = class_name


class Method(FunctionBase):
    def __init__(self, name, result_type, class_name):
        super(Method, self).__init__(name)
        self.result_type = result_type
        self.class_name = class_name

    def __str__(self):
        result = super(Method, self).__str__()
        if self.result_type != "void":
            result += os.linesep + indent_block(
                "Returns (%s)" % self.result_type, 1)
        return result


class Template:
    def __init__(self):
        self.template_types = []

    def __str__(self):
        return indent_block(os.linesep.join(
            ["Template type '%s'" % tt for tt in self.template_types]), 1)


class TemplateClass(Clazz, Template):
    def __init__(self, filename, namespace, name):
        Clazz.__init__(self, filename, namespace, name)
        Template.__init__(self)
        self.ignored = False

    def __str__(self):
        result = Clazz.__str__(self)
        result += os.linesep + Template.__str__(self)
        return result


class TemplateFunction(Function, Template):
    def __init__(self, filename, namespace, name, result_type):
        Function.__init__(self, filename, namespace, name, result_type)
        Template.__init__(self)

    def __str__(self):
        result = Function.__str__(self)
        result += os.linesep + Template.__str__(self)
        return result


class TemplateMethod(Method, Template):
    def __init__(self, name, result_type, class_name):
        Method.__init__(self, name, result_type, class_name)
        Template.__init__(self)

    def __str__(self):
        result = Method.__str__(self)
        result += os.linesep + Template.__str__(self)
        return result


class Param(AstNode):
    def __init__(self, name, tipe):
        super(Param, self).__init__()
        self.name = name
        self.tipe = tipe
        self.default_value = None

    def __str__(self):
        result = "Parameter (%s) %s" % (self.tipe, self.name)
        if self.default_value is not None:
            result += " = " + str(self.default_value)
        return result


class Field(AstNode):
    def __init__(self, name, tipe, class_name):
        super(Field, self).__init__()
        self.name = name
        self.tipe = tipe
        self.class_name = class_name
        self.ignored = False

    def __str__(self):
        return "Field (%s) %s" % (self.tipe, self.name)


class Includes:
    def __init__(self):
        self.numpy = False
        self.stl = {"vector": False,
                    "string": False,
                    "deque": False,
                    "list": False,
                    "map": False,
                    "pair": False,
                    "queue": False,
                    "set": False,
                    "stack": False}
        self.deref = False

    def add_include_for(self, tname):
        if self._part_of_tname(tname, "bool"):
            self.boolean = True
        for t in self.stl.keys():
            if self._part_of_tname(tname, t):
                self.stl[t] = True

    def add_include_for_deref(self):
        self.deref = True

    def _part_of_tname(self, tname, subtname):
        return (tname == subtname or tname.startswith(subtname) or
                ("<" + subtname + ">") in tname or
                ("<" + subtname + ",") in tname or
                (", " + subtname + ">") in tname or
                ("[" + subtname + "]") in tname or
                ("[" + subtname + ",") in tname or
                (", " + subtname + "]") in tname)

    def declarations_import(self):
        includes = "from libcpp cimport bool" + os.linesep

        for t in self.stl.keys():
            if self.stl[t]:
                includes += ("from libcpp.%(type)s cimport %(type)s"
                             % {"type": t}) + os.linesep

        return includes

    def implementations_import(self):
        includes = "from libcpp cimport bool" + os.linesep
        if self.numpy:
            includes += "cimport numpy as np" + os.linesep
            includes += "import numpy as np" + os.linesep

        for t in self.stl.keys():
            if self.stl[t]:
                includes += ("from libcpp.%(type)s cimport %(type)s"
                             % {"type": t}) + os.linesep

        if self.deref:
            includes += ("from cython.operator cimport dereference as deref" +
                         os.linesep)
        includes += "cimport _declarations as cpp" + os.linesep
        return includes


class TypeInfo:
    def __init__(self, asts=[], config=Config(), typedefs={}):
        self.classes = self._collect_classes(asts, config)
        self.typedefs = {typedef.tipe: typedef.underlying_type for ast in asts
                         for typedef in ast.nodes
                         if hasattr(typedef, "underlying_type")}
        self.typedefs.update(typedefs)
        self.enums = [enum.tipe for ast in asts
                      for enum in ast.nodes if hasattr(enum, "tipe")]
        self.spec = {}

    def _collect_classes(self, asts, config):
        specializations = config.registered_template_specializations
        classes = []
        for ast in asts:
            for clazz in ast.nodes:
                template = False
                for key in specializations:
                    if clazz.name == key:
                        template = True
                        for name, _ in specializations[key]:
                            classes.append(name)
                        break
                if not template and isinstance(clazz, Clazz):
                    classes.append(clazz.name)
        return classes

    def attach_specialization(self, spec):
        self.spec = spec

    def remove_specialization(self):
        self.spec = {}

    def underlying_type(self, tname):
        while tname in self.typedefs or tname in self.spec:
            if tname in self.typedefs:
                tname = self.typedefs[tname]
            else:
                tname = self.spec[tname]
        return tname

    def get_specialization(self, tname):
        return self.spec.get(tname, tname)