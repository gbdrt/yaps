indent_size=2

class LabeledString(object):
    def __init__(self, label, str):
        self.label = label
        self.str = str

    def __str__(self):
        return self.str

class LineWithSourceMap(object):
    def __init__(self, line):
        self.line = line

    def __str__(self):
        return ''.join(map(lambda x: x.str, self.line))

    def __getitem__(self, i):
        curIndex = 0
        curChar = 0
        while curIndex < len(self.line):
            elem = self.line[curIndex]
            curChar += len(elem.str)
            if i < curChar:
                return elem.label
            curIndex+=1
        # If it is past the end of the line, just blame the last element
        if self.line:
            return self.line[-1].label
            
class StringWithSourceMap(object):
    def __init__(self, lines, lastData):
        self.lines = []
        for l in lines:
            self.lines.append(LineWithSourceMap(l))
        self.lines.append(LineWithSourceMap(lastData))

    def __str__(self):
        return '\n'.join(map(str, self.lines))
    
    def __getitem__(self, i):
        return self.lines[i]

class LabeledRope(object):
    def __init__(self, strings=[]):
        self.lines = []
        self.lastLine = []
        self.lastLine.extend(strings)

    def append(self, x):
        self.lastLine.append(x)

    def extend(self, x):
        self.lastLine.extend(x)

    def __iadd__(self, x):
        self.append(x)
        return self

    def newline(self):
        self.lines.append(self.lastLine)
        self.lastLine = []

    def result(self):
        return StringWithSourceMap(self.lines, self.lastLine)
    
    def __str__(self):
        return str(self.result())
    
class IR(object):
    def to_stan(self, acc, indent=0):
        acc += self.mkString("NOT YET IMPLEMENTED: " + str(self), indent)

    def mkString(self, str, indent=0):
        return LabeledString(self, (" "*(indent*indent_size)+str))

    def start_block(self, acc, name, indent=0):
        acc += self.mkString(name + " {", indent)
        acc.newline()

    def end_block(self, acc, indent=0):
        acc += self.mkString("}", indent)
        acc.newline()



class Program(IR):
    # Returns an object that can be converted to a strings
    # or can be indexed as result[line][col] to get the IR object
    # responsible for creating that string
    def to_mapped_string(self):
        ret = LabeledRope()
        self.to_stan(ret, 0)
        return ret.result()

    def __init__(self, blocks):
        self.blocks = blocks

    def to_stan(self, acc, indent=0):
        def block_helper(name):
            if(name in self.blocks):
                self.blocks[name].to_stan(acc, indent)
        
        names = [
            "data", 
            "parameters", 
            "transformed_parameters",
            "model", 
            "generated_quantities"]

        for n in names:
            block_helper(n)
        
# Program Blocks (Section 6)
class ProgramBlock(IR):
    def __init__(self, body=[]):
        self.body = []


class FunctionsBlock(ProgramBlock):
    def __init__(self, fdecls=[]):
        self.fdecls = fdecls


class DataBlock(ProgramBlock):
    def __init__(self, vdecls=[]):
        self.vdecls = vdecls

    def to_stan(self, acc, indent=0):
        self.start_block(acc, "data", indent)
        for b in self.vdecls:
            b.to_stan(acc, indent+1)
            acc.newline()
        self.end_block(acc, indent)


class TransformedDataBlock(ProgramBlock):
    def __init__(self, vdecls=[], stmts=[]):
        self.vdecls = vdecls
        self.stmts = stmts


class ParametersBlock(ProgramBlock):
    def __init__(self, vdecls=[]):
        self.vdecls = vdecls

    def to_stan(self, acc, indent=0):
        self.start_block(acc, "parameters", indent)
        for b in self.vdecls:
            b.to_stan(acc, indent+1)
            acc.newline()
        self.end_block(acc, indent)


class TransformedParametersBlock(ProgramBlock):
    def __init__(self, vdecls=[], stmts=[]):
        self.vdecls = vdecls
        self.stmts = stmts

    def to_stan(self, acc, indent=0):
        self.start_block(acc, "transformed parameters", indent)
        for b in self.vdecls:
            b.to_stan(acc, indent+1)
            acc.newline()

        for b in self.stmts:
            b.to_stan(acc, indent+1)
            acc.newline()
        self.end_block(acc, indent)



class ModelBlock(ProgramBlock):
    def __init__(self, vdecls=[], stmts=[]):
        self.vdecls = vdecls
        self.stmts = stmts

    def to_stan(self, acc, indent=0):
        self.start_block(acc, "model", indent)
        for b in self.vdecls:
            b.to_stan(acc, indent+1)
            acc.newline()
        for b in self.stmts:
            b.to_stan(acc, indent+1)
            acc.newline()
        self.end_block(acc, indent)


class GeneratedQuantities(ProgramBlock):
    def __init__(self, vdecls=[], stmts=[]):
        self.vdecls = vdecls
        self.stmts = stmts

    def to_stan(self, acc, indent=0):
        self.start_block(acc, "generated quantities", indent)
        for b in self.vdecls:
            b.to_stan(acc, indent+1)
            acc.newline()
        for b in self.stmts:
            b.to_stan(acc, indent+1)
            acc.newline()
        self.end_block(acc, indent)

# stmts (Section 5)


class Statement(IR):
    pass


class AssignStmt(Statement):
    def __init__(self, lval, op, exp):
        self.lval = lval
        self.op = op
        self.exp = exp


class SamplingStmt(Statement):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def to_stan(self, acc, indent=0):
        self.lhs.to_stan(acc, indent)
        acc += self.mkString(" ~ ")
        self.rhs.to_stan(acc)
        acc += self.mkString(";")


class ForStmt(Statement):
    def __init__(self, var, iter, body):
        self.var = var
        self.iter = iter
        self.body = body


class ConditionalStmt(Statement):
    def __init__(self, cond, exp, alt):
        self.cond = cond
        self.exp = exp
        self.alt = alt


class WhileStmt(Statement):
    def __init__(self, cond, stmt):
        self.cond = cond
        self.stmt = stmt


class Block(Statement):
    def __init__(self, vdecls=[], stmts=[]):
        self.vdecls = vdecls
        self.stmts = stmts


class CallStmt(Statement):
    def __init__(self, id, args):
        self.id = id
        self.args = args

    def to_stan(self, acc, indent=0):
        acc += self.mkString(self.id, indent)
        acc += self.mkString("(")
        first = True
        for a in self.args:
            if first:
                first = False
            else:
                acc += self.mkString(",")
            a.to_stan(acc)
        acc += self.mkString(")")

class BreakStmt(Statement):
    pass


class ContinueStmt(Statement):
    pass


# expessions (Section 4)
class Expression(IR):
    pass


class Atom(Expression):
    pass


class Constant(Atom):
    def __init__(self, value):
        self.value = value

    def to_stan(self, acc, indent=0):
        acc += self.mkString(str(self.value), indent)


class Variable(Atom):
    def __init__(self, id):
        self.id = id
    def to_stan(self, acc, indent=0):
        acc += self.mkString(self.id, indent)


class VectorExpr(Atom):
    pass


class ArrayExpr(Atom):
    pass


class Subscript(Atom):
    def __init__(self, val, slice):
        self.val = val
        self.slice = slice


class Binop(Expression):
    def __init__(self, op, lhs, rhs):
        self.op = op
        self.lhs = lhs
        self.rhs = rhs


class Unop(Expression):
    def __init__(self, op, expr):
        self.op = op
        self.rhs = expr

    def to_stan(self, acc, indent=0):
        self.op.to_stan(acc, indent)
        acc += self.mkString("(")
        self.rhs.to_stan(acc, indent)
        acc += self.mkString(")")
        first = True



class Call(Expression):
    def __init__(self, id, args):
        self.id = id
        self.args = args

    def to_stan(self, acc, indent=0):
        acc += self.mkString(self.id, indent)
        acc += self.mkString("(")
        first = True
        for a in self.args:
            if first:
                first = False
            else:
                acc += self.mkString(",")
            a.to_stan(acc)
        acc += self.mkString(")")

# Declarations
class VariableDecl(IR):
    def __init__(self, id, ty, val=None):
        self.id = id
        self.ty = ty
        self.val = val

    def to_stan(self, acc, indent=0):
        self.ty.to_stan(acc, self.mkString(self.id), indent)
        if self.val is not None:
            acc += self.mkString(" = ")
            self.val.to_stan(acc)
        acc += self.mkString(";")


class Type(IR):
    def __init__(self, kind, cstrts=None, dims=None):
        self.kind = kind
        self.cstrts = cstrts
        self.dims = dims

    def constraint_to_stan(self, acc, cstr, indent=0):
        lower, upper=cstr
        acc += self.mkString(str(lower) + "=", indent)
        upper.to_stan(acc)


    def to_stan(self, acc, id, indent=0):
        acc += self.mkString(self.kind, indent)
        if self.cstrts:
            acc += self.mkString("<")
            first = True
            for cstr in self.cstrts:
                if first:
                    first = False
                else:
                    acc += self.mkString(",")
                self.constraint_to_stan(acc, cstr)

            acc += self.mkString(">")
        acc += self.mkString(" ")
        acc += id
        if self.dims is not None:
            acc += self.mkString("[" + str(self.dims) + "]")

# Operator


class Operator(IR):
    pass


class EQ(Operator):
    def to_stan(self, acc, indent=0):
        acc += self.mkString("==", indent)



class NEQ(Operator):

    def to_stan(self, acc, indent=0):
        acc += self.mkString("!=", indent)


class SUB(Operator):    
    def to_stan(self, acc, indent=0):
        acc += self.mkString("-", indent)


class PLUS(Operator):
    def to_stan(self, acc, indent=0):
        acc += self.mkString("+", indent)


class MULT(Operator):
    def to_stan(self, acc, indent=0):
        acc += self.mkString("*", indent)



class DIV(Operator):
    def to_stan(self, acc, indent=0):
        acc += self.mkString("/", indent)

