import clang_util
import file_parser
import util
import parser_addition
import re
from clang.cindex import TypeKind

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


class SimpleToken(object):
    def __init__(self, spelling):
        self.spelling = spelling


def same_tokens(tokens, other_tokens):
    if len(tokens) != len(other_tokens):
        return False
    for i in range(len(tokens)):
        if tokens[i].spelling != other_tokens[i].spelling:
            return False
    return True


def contains(name, tokens):
    for token in tokens:
        if token.spelling == name:
            return True
    return False


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


class Alias(Tokens):
    def __init__(self, name, tokens):
        self.type = ALIAS
        self.name = name
        super(Alias,self).__init__(tokens)

    def visit(self,visitor):
        return visitor.visit_alias(self)


def get_alias_from_text(name, text):
    return Alias(name, [SimpleToken(spelling) for spelling in text.split(' ')])


def sequence_from_text(text):
    return [SimpleToken(entry) for entry in text.split(' ')]


def contains_sequence(tokens, sub_tokens):
    if len(sub_tokens) > len(tokens):
        return False
    for offset in range(len(tokens) - len(sub_tokens)):
        found_sequence = True
        for index in range(len(sub_tokens)):
            if sub_tokens[index] != tokens[offset + index]:
                found_sequence = False
        if found_sequence:
            return True
    return False


def returns_this(function):
    remaining_tokens = function.tokens[get_declaration_end_index(function.name, function.tokens):]
    return contains_sequence(remaining_tokens, sequence_from_text('return * this ;'))


def returns_class_ref(classname,function):
    index, offset = find_function_name(function.name, function.tokens)
    return util.concat(function.tokens[:index], ' ') in ['const ' + classname + ' & ',
                                                         classname + ' & ']


def get_table_return_type(function):
    index, offset = find_function_name(function.name, function.tokens)
    return_type = util.concat(function.tokens[:index], ' ')
    if return_type in ['const ' + function.classname + ' & ',
                       function.classname + ' & ']:
        return 'void '
    if return_type == function.classname + ' ':
        return

    if returns_this(function):
        return 'void '

    return util.concat(function.tokens[:index], ' ')


def get_function_name_for_tokens(name):
    if 'operator' in name:
        return 'operator ' + name[8:]
    return name


def get_function_name_for_type_erasure(function):
    arg_extension = ''
    args = get_function_arguments(function)
    for arg in args:
        arg_extension += '_' + arg.type()
    arg_extension = arg_extension.replace('&','_ref').replace('*','_ptr').replace(' ','_')
    arg_extension = re.sub(r'<|>|\[|\]\(|\)\{\}', '', arg_extension)
    if function.name == 'operator()':
        return 'call' + arg_extension
    elif function.name == 'operator=':
        return 'assignment' + arg_extension
    elif function.name == 'operator+=':
        return 'add' + arg_extension
    elif function.name == 'operator*=':
        return 'multiply' + arg_extension
    elif function.name == 'operator-=':
        return 'subtract' + arg_extension
    elif function.name == 'operator-':
        return 'negate' + arg_extension
    elif function.name == 'operator/=':
        return 'divide' + arg_extension
    elif function.name == 'operator==':
        return 'compare' + arg_extension
    return function.name


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


def uses_type(function,typename):
    for token in function.tokens:
        if token.spelling == typename:
            return True
    return False


def replace_in_tokens(old_spelling, new_spelling, tokens):
    for token in tokens:
        if token.spelling == old_spelling:
            token.spelling = new_spelling


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


def const_specifier(function):
    return 'const ' if is_const(function) else ''


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


def get_function_from_text(classname, functionname, return_str, text, function_type='function'):
    return Function(classname, functionname, return_str, [SimpleToken(spelling) for spelling in text.split(' ')], function_type)


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


class CppFileParser(file_parser.FileProcessor):
    def __init__(self):
        self.scope = Namespace('global')

    def process_inclusion_directive(self, data, cursor):
        self.scope.add(InclusionDirective(clang_util.parse_inclusion_directive(data, cursor).replace('#include ', '').replace('\n', '')))

    def process_open_include_guard(self, filename):
        self.scope.add(ScopeEntry('include_guard', parser_addition.extract_include_guard(filename)))

    def process_headers(self, headers):
        self.scope.add(ScopeEntry('headers', headers))

    def process_open_namespace(self, data, cursor):
        self.scope.add(Namespace(cursor.spelling, clang_util.get_tokens(data.tu, cursor)))

    def process_close_namespace(self):
        self.scope.close()

    def process_open_class(self, data, cursor):
        if clang_util.get_tokens(data.tu, cursor)[2].spelling == clang_util.semicolon:
            self.scope.add(Class(data.current_struct.spelling, clang_util.get_tokens(data.tu, cursor)[:3]))
#            self.scope.add(ForwardDeclaration(util.concat(clang_util.get_tokens(data.tu, cursor)[:3], ' ')))
        else:
            self.scope.add(Class(data.current_struct.spelling, clang_util.get_tokens(data.tu, cursor)))

    def process_open_struct(self, data, cursor):
        if clang_util.get_tokens(data.tu, cursor)[2].spelling == clang_util.semicolon:
            self.scope.add(Struct(data.current_struct.spelling, clang_util.get_tokens(data.tu, cursor)[:3]))
#            self.scope.add(ForwardDeclaration(util.concat(clang_util.get_tokens(data.tu, cursor)[:3], ' ')))
        else:
            self.scope.add(Struct(data.current_struct.spelling, clang_util.get_tokens(data.tu, cursor)))

    def process_close_class(self):
        if self.scope.get_open_scope().get_type() == NAMESPACE:
            return
        self.scope.close()

    def process_function(self, data, cursor):
        classname = ''
        if data.current_struct.spelling:
            classname = data.current_struct.spelling
        current_scope = self.scope.get_open_scope()
        
        tokens = clang_util.get_tokens(data.tu, cursor)
        tokens = tokens[:get_body_end_index(cursor.spelling, tokens)]
        if current_scope.get_tokens() and not tokens[-1].spelling == clang_util.semicolon:
            tokens = clang_util.get_all_tokens(tokens, current_scope.get_tokens())

        function_type = FUNCTION
        if clang_util.is_function_template(cursor.kind):
            function_type = FUNCTION_TEMPLATE
        self.scope.add(Function(classname, cursor.spelling, cursor.result_type.kind != TypeKind.VOID and 'return ' or '', tokens, function_type))

    def process_function_template(self, data, cursor):
        self.process_function(data, cursor)

    def process_constructor(self, data, cursor):
        classname = ''
        if data.current_struct.spelling:
            classname = data.current_struct.spelling
        current_scope = self.scope.get_open_scope()
        tokens = clang_util.get_tokens(data.tu, cursor)
        tokens = tokens[:get_body_end_index(cursor.spelling, tokens)]
        if current_scope.get_tokens() and not tokens[-1].spelling == clang_util.semicolon:
            tokens = clang_util.get_all_tokens(tokens, current_scope.get_tokens())
        self.scope.add(Function(classname, cursor.spelling, cursor.result_type.kind != TypeKind.VOID and 'return ' or '', tokens, CONSTRUCTOR))

    def process_destructor(self, data, cursor):
        self.process_function(data, cursor)

    def process_type_alias(self,data,cursor):
        self.scope.add(Alias(cursor.spelling, clang_util.get_tokens(data.tu, cursor)))

    def process_variable_declaration(self,data,cursor):
        tokens = clang_util.get_tokens(data.tu, cursor)
        if tokens[-1].spelling != clang_util.semicolon and self.scope.get_open_scope().get_tokens():
            tokens = clang_util.get_all_variable_tokens(tokens, self.scope.get_open_scope().get_tokens())

        variable_declaration = util.concat(tokens, ' ')
        # in case that an underlying type is specified,
        # clang interprets enums at variables.
        # filter out these cases:
        if 'enum ' in variable_declaration:
            #TODO try to find a workaround for this
            return
        if clang_util.get_tokens(data.tu, cursor)[0].spelling == 'static':
            self.scope.add(StaticVariable(variable_declaration))
        else:
            self.scope.add(Variable(variable_declaration))

    def process_member_variable_declaration(self,data,cursor):
        self.process_variable_declaration(data, cursor)

    def process_forward_declaration(self,data,cursor):
        pass

    def process_enum(self,data,cursor):
        self.scope.add(ScopeEntry('enum', clang_util.get_enum_definition(data.tu, cursor)))

    def process_access_specifier(self, data, cursor):
        self.scope.add(AccessSpecifier(clang_util.get_tokens(data.tu, cursor)[0].spelling))


class Visitor(object):
    def visit(self,visited):
        pass

    def visit_function(self,function):
        return self.visit(function)

    def visit_template_function(self,function):
        return self.visit_function(function)

    def visit_constructor(self,constructor):
        return self.visit_function(constructor)

    def visit_destructor(self,destructor):
        return self.visit_function(destructor)

    def visit_operator(self,operator):
        return self.visit_function(operator)

    def visit_class(self,class_):
        return self.visit(class_)

    def visit_forward_declaration(self,forward_declaration):
        return self.visit(forward_declaration)

    def visit_template_class(self,template_class):
        return self.visit(template_class)

    def visit_namespace(self,namespace):
        return self.visit(namespace)

    def visit_inclusion_directive(self,inclusion_directive):
        return self.visit(inclusion_directive)

    def visit_access_specifier(self,access_specifier):
        return self.visit(access_specifier)

    def visit_variable(self,variable):
        return self.visit(variable)

    def visit_static_variable(self,variable):
        return self.visit(variable)

    def visit_alias(self,alias):
        return self.visit(alias)

    def visit_comment(self,comment):
        return self.visit(comment)


class RecursionVisitor(Visitor):
    def visit_class(self,class_):
        for entry in class_.content:
            entry.visit(self)

    def visit_template_class(self,template_class):
        for entry in template_class.content:
            entry.visit(self)

    def visit_namespace(self,namespace):
        for entry in namespace.content:
            entry.visit(self)


class ExtractPublicProtectedPrivateSections(RecursionVisitor):
    def __init__(self):
        self.private_section = []
        self.protected_section = []
        self.public_section = []
        self.access_specifier = PRIVATE

    def visit_access_specifier(self,access_specifier):
        self.access_specifier = access_specifier.value

    def visit(self,entry):
        if self.access_specifier == PRIVATE:
            self.private_section.append(entry)
        elif self.access_specifier == PROTECTED:
            self.protected_section.append(entry)
        else:
            self.public_section.append(entry)


def append_comment(comment,group):
    if comment:
        group.append(comment)
    return None


class ExtractTypes(Visitor):
    def __init__(self):
        self.aliases = []
        self.static_variables = []
        self.constructors = []
        self.destructor = []
        self.operators = []
        self.functions = []
        self.forward_declarations = []
        self.variables = []
        self.comment = None

    def visit_comment(self,comment):
        self.comment = comment

    def visit_function(self,function):
        if function.type in [ASSIGNMENT_OPERATOR]:
            self.comment = append_comment(self.comment, self.operators)
            self.operators.append(function)
        if function.type in [FUNCTION, FUNCTION_TEMPLATE]:
            if function.name.startswith('operator'):
                self.comment = append_comment(self.comment, self.operators)
                self.operators.append(function)
            else:
                self.comment = append_comment(self.comment, self.functions)
                self.functions.append(function)
        elif function.type in [CONSTRUCTOR, CONSTRUCTOR_TEMPLATE]:
            self.comment = append_comment(self.comment, self.constructors)
            self.constructors.append(function)
        elif function.type == DESTRUCTOR:
            self.comment = append_comment(self.comment, self.destructor)
            self.destructor.append(function)

    def visit_variable(self,variable):
        self.comment = append_comment(self.comment,self.variables)
        self.variables.append(variable)

    def visit_static_variable(self,variable):
        self.comment = append_comment(self.comment,self.static_variables)
        self.static_variables.append(variable)

    def visit_alias(self,alias):
        self.comment = append_comment(self.comment,self.aliases)
        self.aliases.append(alias)

    def visit_forward_declaration(self,forward_declaration):
        self.forward_declarations.append(forward_declaration)


def extend_section(new_section, section_part, with_separator=True):
    if new_section and section_part and with_separator:
        new_section.append(Separator())
    new_section.extend(section_part)


def sort_section(section):
    type_extractor = ExtractTypes()
    for entry in section:
        entry.visit(type_extractor)

    new_section = []
    new_section.extend(type_extractor.aliases)
    extend_section(new_section, type_extractor.static_variables)
    extend_section(new_section, type_extractor.constructors)
    extend_section(new_section, type_extractor.destructor)
    extend_section(new_section, type_extractor.operators)
    extend_section(new_section, type_extractor.functions)
    extend_section(new_section, type_extractor.forward_declarations)
    extend_section(new_section, type_extractor.variables, with_separator=False)
    return new_section


class SortClass(RecursionVisitor):
    def visit_class(self,class_):
        section_extractor = ExtractPublicProtectedPrivateSections()
        class_.visit(section_extractor)
        section_extractor.public_section = sort_section(section_extractor.public_section)
        section_extractor.protected_section = sort_section(section_extractor.protected_section)
        section_extractor.private_section = sort_section(section_extractor.private_section)

        class_.content = []
        if section_extractor.public_section:
            class_.content.append(AccessSpecifier(PUBLIC))
            class_.content.extend(section_extractor.public_section)
        if section_extractor.protected_section:
            class_.content.append(AccessSpecifier(PROTECTED))
            class_.content.extend(section_extractor.protected_section)
        if section_extractor.private_section:
            class_.content.append(AccessSpecifier(PRIVATE))
            class_.content.extend(section_extractor.private_section)


def remove_inclusion_directives(main_scope):
    new_scope = []
    for entry in main_scope.content:
        if not is_inclusion_directive(entry):
            new_scope.append(entry)
    main_scope.content = new_scope


def remove_duplicate_inclusion_directives(main_scope):
    new_scope = []
    for entry in main_scope.content:
        if is_inclusion_directive(entry):
            in_new_scope = False
            for new_entry in new_scope:
                if is_inclusion_directive(new_entry) and new_entry.value == entry.value:
                    in_new_scope = True
                    break
            if not in_new_scope:
                new_scope.append(entry)
        else:
            new_scope.append(entry)
    main_scope.content = new_scope


def prepend_inclusion_directives(main_scope, inclusion_directives):
    for inclusion_directive in reversed(inclusion_directives):
        main_scope.content.insert(0, inclusion_directive)


def append_inclusion_directive(main_scope, inclusion_directive):
    for i in range(len(main_scope.content)):
        if not is_inclusion_directive(main_scope.content[i]):
            main_scope.content.insert(i, inclusion_directive)
            return


def append_inclusion_directives(main_scope, inclusion_directives):
    for inclusion_directive in inclusion_directives:
        append_inclusion_directive(main_scope, inclusion_directive)



def add_comment(new_content, entry, comments):
    comment = util.get_comment(comments, entry)
    if comment:
        new_content.append(Comment(comment))


def add_comments(scope, comments):
    new_content = []
    for entry in scope.content:
        if is_namespace(entry):
            add_comment(new_content, 'namespace ' + entry.name, comments)
            add_comments(entry, comments)
        elif is_class(entry) or is_struct(entry):
            add_comment(new_content, entry.type + ' ' + entry.name, comments)
            add_comments(entry, comments)
        elif entry.type in [FUNCTION, CONSTRUCTOR, DESTRUCTOR, FUNCTION_TEMPLATE, ASSIGNMENT_OPERATOR]:
            add_comment(new_content, entry.get_declaration(), comments)
        elif entry.type == ALIAS:
            add_comment(new_content, util.concat(entry.tokens, ' '), comments)
        new_content.append(entry)
    scope.content = new_content
