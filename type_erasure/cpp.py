import clang_util
import util


INCLUDE_GUARD           = 'include guard'
INCLUSION_DIRECTIVE     = 'include'
ACCESS_SPECIFIER        = 'access specifier'
ALIAS                   = 'alias'
CLASS                   = 'class'
CLASS_TEMPLATE          = 'class template'
CONSTRUCTOR             = 'constructor'
CONSTRUCTOR_TEMPLATE    = 'constructor template'
ASSIGNMENT_OPERATOR     = 'assignment operator'
DESTRUCTOR              = 'destructor'
ENUM                    = 'enum'
FUNCTION                = 'function'
FUNCTION_TEMPLATE       = 'function template'
NAMESPACE               = 'namespace'
PRIVATE                 = 'private'
PROTECTED               = 'protected'
PUBLIC                  = 'public'
STATIC_VARIABLE         = 'static variable'
STRUCT                  = 'struct'
FORWARD_DECLARATION     = 'forward declaration'
VARIABLE                = 'variable'
COMMENT                 = 'comment'
SEPARATOR               = 'separator'
scoped_types            = [NAMESPACE, CLASS, STRUCT]
signedness              = ['signed', 'unsigned']
builtin_integer_types   = ['int', 'short', 'long', 'long long', 'char', 'wchar_t', 'wchar16_t', 'wchar32_t']
builtin_float_types     = ['float', 'double', 'long double' ]


def is_include_guard(entry):
    return entry.type == INCLUDE_GUARD


def is_class(entry):
    return entry.type == CLASS


def is_struct(entry):
    return entry.type == STRUCT


def is_namespace(entry):
    return entry.type == NAMESPACE


def is_function(entry):
    return entry.type == FUNCTION


def is_alias(entry):
    return entry.type == ALIAS


def is_access_specifier(entry):
    return entry.type == ACCESS_SPECIFIER


def is_inclusion_directive(entry):
    return entry.type == INCLUSION_DIRECTIVE


def is_constructor(entry):
    return entry.type == CONSTRUCTOR


def is_destructor(entry):
    return entry.type == DESTRUCTOR


class InTypeCounter(object):
    def __init__(self, open_parens = 0, open_brackets = 0, open_braces = 0):
        self.initial_open_parens = open_parens
        self.open_parens = self.initial_open_parens
        self.initial_open_brackets = open_brackets
        self.open_brackets = self.initial_open_brackets
        self.initial_open_braces = open_braces
        self.open_braces = self.initial_open_braces

    def process(self,spelling):
        if spelling == clang_util.open_paren:
            self.open_parens += 1
        if spelling == clang_util.close_paren:
            self.open_parens -= 1
        if spelling == clang_util.open_bracket:
            self.open_brackets += 1
        if spelling == clang_util.close_bracket:
            self.open_brackets -= 1
        if spelling == clang_util.open_brace:
            self.open_braces += 1
        if spelling == clang_util.close_brace:
            self.open_braces -= 1

    def initial_state(self):
        return self.open_parens == self.initial_open_parens and \
               self.open_brackets == self.initial_open_brackets and \
               self.open_braces == self.initial_open_braces


class ScopeEntry(object):
    def __init__(self, type, value):
        self.type = type
        self.value = value

    def visit(self,visitor):
        return visitor.visit(self)

    def __str__(self):
        return self.value

    def __cmp__(self, other):
        return self.type == other.type and self.value == other.value


class SimpleToken(object):
    def __init__(self, spelling):
        self.spelling = spelling


class Comment(ScopeEntry):
    def __init__(self,comment):
        super(Comment,self).__init__(COMMENT, comment)

    def visit(self,visitor):
        return visitor.visit_comment(self)

    def __str__(self):
        comment = ''
        for line in self.value.comment:
            comment += line + '\n'
        return comment


class ForwardDeclaration(ScopeEntry):
    def __init__(self,forward_declaration):
        super(ForwardDeclaration,self).__init__(FORWARD_DECLARATION, forward_declaration)

    def visit(self,visitor):
        return visitor.visit_forward_declaration(self)


class IncludeGuard(ScopeEntry):
    def __init__(self, include_guard):
        super(IncludeGuard, self).__init__(INCLUDE_GUARD, include_guard)


class Separator(ScopeEntry):
    def __init__(self):
        super(Separator,self).__init__(SEPARATOR,'\n')


class AccessSpecifier(ScopeEntry):
    def __init__(self,access_specifier):
        super(AccessSpecifier,self).__init__(ACCESS_SPECIFIER,access_specifier)

    def visit(self,visitor):
        return visitor.visit_access_specifier(self)


public_access = AccessSpecifier(PUBLIC)
protected_access = AccessSpecifier(PROTECTED)
private_access = AccessSpecifier(PRIVATE)


class InclusionDirective(ScopeEntry):
    def __init__(self,inclusion_directive):
        super(InclusionDirective,self).__init__(INCLUSION_DIRECTIVE, inclusion_directive)

    def visit(self,visitor):
        return visitor.visit_inclusion_directive(self)


class Variable(ScopeEntry):
    def __init__(self,variable):
        super(Variable,self).__init__(VARIABLE,variable)

    def visit(self,visitor):
        return visitor.visit_variable(self)


class StaticVariable(ScopeEntry):
    def __init__(self,static_variable):
        super(StaticVariable,self).__init__(STATIC_VARIABLE,static_variable)

    def visit(self,visitor):
        return visitor.visit_static_variable(self)


class Tokens(object):
    def __init__(self, tokens):
        self.tokens = [SimpleToken(token.spelling) for token in tokens]

    def get_tokens(self):
        return self.tokens

    def __repr__(self):
        str = ''
        for token in self.tokens:
            # libclang may append comments at the end of a function if there is no new line between.
            # ignore these comments
            if not token.spelling.startswith('//') and not token.spelling.startswith('/*'):
                str += token.spelling + ' '
        return str + '\n'


class Scope(Tokens):
    def __init__(self, type, name, tokens):
        self.type = type
        self.name = name
        self.content = []
        self.open_sub_scope = None
        super(Scope, self).__init__(tokens)

    def get_name(self):
        return self.name

    def get_type(self):
        return self.type

    def add(self, entry):
        if self.open_sub_scope:
            self.open_sub_scope.add(entry)
            return

        if entry.type in scoped_types:
            self.open_sub_scope = entry
        else:
            self.content.append( entry )

    def close(self):
        if self.open_sub_scope:
            if self.open_sub_scope.open_sub_scope:
                self.open_sub_scope.close()
            else:
                self.content.append(self.open_sub_scope)
                self.open_sub_scope = None

    def get_open_scope(self):
        if self.open_sub_scope:
            return self.open_sub_scope.get_open_scope()
        return self


class Class(Scope):
    def __init__(self, name, tokens=[]):
        super(Class,self).__init__(CLASS, name, tokens)

    def visit(self,visitor):
        return visitor.visit_class(self)


class Struct(Scope):
    def __init__(self, name, tokens=[]):
        super(Struct,self).__init__(STRUCT, name, tokens)

    def visit(self,visitor):
        return visitor.visit_class(self)


class TemplateStruct(Scope):
    def __init__(self, name, tokens=[]):
        super(TemplateStruct,self).__init__(STRUCT, name, tokens)

    def visit(self,visitor):
        return visitor.visit_template_class(self)


def get_template_struct_from_text(name, text):
    return TemplateStruct(name, [SimpleToken(spelling) for spelling in text.split(' ')])


class Namespace(Scope):
    def __init__(self, name, tokens=[]):
        super(Namespace,self).__init__(NAMESPACE, name, tokens)

    def visit(self,visitor):
        return visitor.visit_namespace(self)


class Alias(Tokens):
    def __init__(self, name, tokens):
        self.type = ALIAS
        self.name = name
        super(Alias,self).__init__(tokens)

    def visit(self,visitor):
        return visitor.visit_alias(self)


def contains_sequence(tokens, sub_tokens):
    if len(sub_tokens) > len(tokens):
        return False
    for offset in range(len(tokens) - len(sub_tokens) + 1):
        found_sequence = True
        for index in range(len(sub_tokens)):
            if sub_tokens[index].spelling != tokens[offset + index].spelling:
                found_sequence = False
        if found_sequence:
            return True
    return False


class FunctionArgument(Tokens):
    def is_const(self):
        counter = InTypeCounter()
        for i in range(len(self.tokens)):
            spelling = self.tokens[i].spelling
            counter.process(spelling)
            if counter.initial_state() and spelling == 'const' and not (i and self.tokens[i-1].spelling == '*'):
                return True
        return False

    def type(self):
        return util.concat(self.tokens[:get_name_index(self)], ' ')

    def decayed_type(self):
        type = self.type()
        if type.endswith('* '):
            return type

        if type.startswith('const '):
            type = type[6:]
        if type.endswith('& '):
            type = type[:-2]

        return type.replace(' ','')

    def is_rvalue(self):
        last_type_token = self.tokens[get_name_index(self) - 1]
        return last_type_token.spelling == '&&'

    def is_value(self):
        last_type_token = self.tokens[get_name_index(self) - 1]
        return '&' not in last_type_token.spelling and '*' not in last_type_token.spelling

    def is_forward_reference(self):
        return False

    def name(self):
        return self.tokens[get_name_index(self)].spelling

    def in_declaration(self):
        return str(self)

    def in_single_function_call(self):
        if self.is_forward_reference():
            return 'std::forward<' + self.type() + '>( ' + self.name() + ' )'
        if self.is_rvalue() or self.is_value():
            return 'std::move( ' + self.name() + ' )'
        return self.name()


class Function(Tokens):
    def __init__(self, classname, functionname, return_str, tokens, function_type=FUNCTION):
        self.type = function_type
        self.classname = classname
        self.return_str = return_str
        self.name = functionname
        self.tokens = [ SimpleToken(token.spelling) for token in tokens[:get_body_end_index(self.name, tokens)] ]
        if self.classname == '':
            index, offset = find_function_name(self.name, self.tokens)
            if index > 1 and self.tokens[index-1].spelling == '::':
                self.classname = self.tokens[index-2].spelling
                self.tokens.pop(index-1)
                self.tokens.pop(index-2)

    def get_declaration(self):
        return util.concat(self.tokens[:get_declaration_end_index(self.name, self.tokens)], ' ')

    def get_in_place_definition(self):
        definition = ''
        for token in self.tokens:
            definition += token.spelling + ' '
        return definition + '\n'

    def get_definition(self):
        if self.classname == '':
            return self.get_in_place_definition()
        definition = ''
        index, offset = find_function_name(self.name, self.tokens)
        for i in range(len(self.tokens)):
            spelling = self.tokens[i].spelling
            if spelling == 'explicit':
                continue
            if i == index:
                definition += self.classname + '::' + spelling + ' '
            else:
                definition += spelling + ' '
        return definition + '\n'

    def visit(self,visitor):
        if self.type in [FUNCTION_TEMPLATE, CONSTRUCTOR_TEMPLATE]:
            return visitor.visit_template_function(self)
        return visitor.visit_function(self)


def is_special_member_function(function):
    if not function.classname:
        return False
    if is_destructor(function):
        return True
    if is_constructor(function) and len(get_function_arguments(function)) == 0:
        return True

    if is_constructor(function) or function.name == 'operator=':
        args = get_function_arguments(function)
        # default constructor
        if len(args) == 0:
            return True
        # copy or move constructor
        if len(args) == 1 and ( util.same_signature(args[0].type(), function.classname + ' &&') or \
                                util.same_signature(args[0].type(), 'const ' + function.classname + ' &') ):
            return True


def get_function_arguments(function):
    index, offset = find_function_name(function.name, function.tokens)
    end_index = get_arguments_end_index(function.name, function.tokens)
    tokens_of_all_arguments = function.tokens[index+offset:end_index]
    tokens_of_one_argument = []
    arguments = []
    counter = InTypeCounter()
    for token in tokens_of_all_arguments:
        spelling = token.spelling
        counter.process(spelling)
        if counter.initial_state() and spelling == ',':
            arguments.append( FunctionArgument(tokens_of_one_argument) )
            tokens_of_one_argument = []
        else:
            tokens_of_one_argument.append(token)
    if len(tokens_of_one_argument):
        arguments.append(FunctionArgument(tokens_of_one_argument))
    return arguments


def get_function_arguments_in_single_call(function):
    arguments = get_function_arguments(function)
    args_in_single_call = ''
    for arg in arguments:
        args_in_single_call += arg.in_single_function_call()
        if arg is not arguments[-1]:
            args_in_single_call += ' , '
    return args_in_single_call


def get_name_size_in_tokens(name):
    if name.startswith('~'):
        return 2
    if name in ['operator=',
                'operator+',
                'operator-',
                'operator bool',
                'operator+=',
                'operator-=',
                'operator*=',
                'operator/=',
                'operator==',
                'operator^',
                'operator*']:
        return 2
    if name in ['operator()',
                'operator[]']:
        return 3
    return 1


def find_function_name(name, tokens):
    ntokens_for_name_and_bracket = get_name_size_in_tokens(name) + 1
    name_tokens = [SimpleToken(tokens[i].spelling) for i in range(ntokens_for_name_and_bracket)]
    if util.concat(name_tokens) == name + '(':
        return 0, ntokens_for_name_and_bracket

    for i in range(ntokens_for_name_and_bracket, len(tokens)):
        name_tokens.pop(0)
        name_tokens.append(SimpleToken(tokens[i].spelling))
        if util.same_signature(util.concat(name_tokens, ' '), name + '('):
            return i-ntokens_for_name_and_bracket+1, ntokens_for_name_and_bracket


def get_declaration_end_index(name, tokens):
    index, ntokens = find_function_name(name, tokens)

    counter = InTypeCounter()
    counter.process(clang_util.open_paren)
    for i in range(index + ntokens, len(tokens)):
        counter.process(tokens[i].spelling)
        if counter.initial_state():
            index = i + 1
            break

    for i in range(index, len(tokens)):
        if tokens[i].spelling in [clang_util.open_brace, clang_util.semicolon, ':']:
            return i
    return len(tokens)


def get_arguments_end_index(name, tokens):
    index = get_declaration_end_index(name, tokens) - 1
    spelling = tokens[index].spelling
    while spelling != clang_util.close_paren:
        index -= 1
        spelling = tokens[index].spelling
    return index


def get_body_end_index(name, tokens):
    index = get_declaration_end_index(name, tokens)
    if index == len(tokens):
        return index
    if tokens[index].spelling == clang_util.semicolon:
        return index+1

    index = clang_util.get_end_of_member_initialization(index, tokens)

    while tokens[index].spelling != clang_util.open_brace:
        index += 1

    counter = InTypeCounter()
    counter.process(tokens[index].spelling)
    for i in range(index + 1, len(tokens)):
        counter.process(tokens[i].spelling)
        if counter.initial_state():
            return i+1
    return len(tokens)


def get_body_range(name, tokens):
    return [get_declaration_end_index(name,tokens), get_body_end_index(name, tokens)]


def get_name_index(function_argument):
    for i in range(len(function_argument.tokens)):
        if function_argument.tokens[i].spelling == '=':
            return i - 1

    return len(function_argument.tokens) - 1


def returns_class_ref(classname,function):
    index, offset = find_function_name(function.name, function.tokens)
    return util.concat(function.tokens[:index], ' ') in ['const ' + classname + ' & ',
                                                         classname + ' & ']


def uses_type(function,typename):
    for token in function.tokens:
        if token.spelling == typename:
            return True
    return False


def is_deleted(function):
    return len(function.tokens) > 5 and util.concat(function.tokens[-3:], ' ') == '= delete ; '


def is_defaulted(function):
    return len(function.tokens) > 5 and util.concat(function.tokens[-3:], ' ') == '= default ; '


def is_constexpr(function):
    return len(function.tokens) > 4 and (function.tokens[0].spelling  == 'constexpr' or
                                         function.tokens[1].spelling == 'constexpr')


def is_const(function):
    index = get_declaration_end_index(function.name, function.tokens)
    while function.tokens[index].spelling != clang_util.close_paren:
        if function.tokens[index].spelling == 'const':
            return True
        index -= 1
    return False


def is_forward_declaration(class_object):
    for token in class_object.tokens:
        if token.spelling == clang_util.open_brace:
            return False
        if token.spelling == clang_util.semicolon:
            return True
    return False
