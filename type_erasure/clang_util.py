import clang
import re

from clang.cindex import CursorKind
from clang.cindex import TypeKind
import os
from util import trim


semicolon = ';'
open_paren = '('
close_paren = ')'
const_token = 'const'
open_brace = '{'
close_brace = '}'
open_bracket = '<'
close_bracket = '>'
comma = ','


def get_tokens(tu, cursor):
    return [x for x in tu.get_tokens(extent=cursor.extent)]


def get_class_prefix(translation_unit, class_cursor):
    retval = ''
    tokens = get_tokens(translation_unit, class_cursor)

    open_brackets = 0
    for i in range(len(tokens)):
        spelling = tokens[i].spelling
        if spelling == open_brace or spelling == semicolon:
            break
        elif spelling == close_bracket:
            open_brackets -= 1
            if open_brackets == 0:
                retval += spelling + '\n'
                continue
        elif i and not i+1 == len(tokens) and \
                not retval[-1] == open_bracket and \
                not retval[-1] == close_bracket and \
                not retval[-1] == '\n':
            if spelling == open_bracket:
                open_brackets += 1
            retval += ' '
        retval += spelling

    return retval


def without_spaces(spelling):
    return spelling == '::' or spelling == '<' or spelling == '>' or spelling == ','


def get_type_alias(translation_unit, cursor):
    tokens = get_tokens(translation_unit, cursor)
    type_alias = ''
    for token in tokens:
        spelling = token.spelling
        if token == tokens[-1]:
            type_alias += spelling + '\n'
        elif without_spaces(spelling):
            alias_start = (len(type_alias) > 0 and type_alias[:-1] or '')
            type_alias = alias_start + spelling
        elif token == tokens[-2]:
            type_alias += spelling
        else:
            type_alias += spelling + ' '
    return type_alias


def get_typedef(translation_unit, cursor):
    tokens = get_tokens(translation_unit, cursor)
    typedef = ''
    for token in tokens:
        spelling = token.spelling
        if token == tokens[-1]:
            typedef += spelling + '\n'
        elif without_spaces(spelling):
            typedef_start = (len(typedef) > 0 and typedef[:-1] or '')
            typedef = typedef_start + spelling
        elif token == tokens[-2]:
            typedef += spelling
        else:
            typedef += spelling + ' '
    return typedef


def get_type_alias_or_typedef(translation_unit, cursor):
    if is_type_alias(cursor.kind):
        return get_type_alias(translation_unit, cursor)
    if is_typedef(cursor.kind):
        return get_typedef(translation_unit, cursor)


def get_variable_declaration(translation_unit, cursor):
    tokens = get_tokens(translation_unit, cursor)
    variable_declaration = ''
    for token in tokens:
        spelling = token.spelling
        if token == tokens[-1]:
            variable_declaration += spelling + '\n'
        elif token == tokens[-2]:
            variable_declaration += spelling
        else:
            variable_declaration += spelling + ' '
    return variable_declaration


def get_enum_definition(translation_unit, cursor):
    tokens = get_tokens(translation_unit, cursor)
    enum_definition = ''
    for token in tokens:
        enum_definition += token.spelling
        if token == tokens[-1]:
            enum_definition += '\n'
        elif token != tokens[-2]:
            enum_definition += ' '

    return enum_definition


def format_enum_definition(enum_indent, base_indent, enum_definition):
    formatted_definition = ''
    enum_prefix = trim(enum_definition.split(open_brace)[0])
    formatted_definition += enum_indent + enum_prefix + '\n'
    formatted_definition += enum_indent + open_brace

    enum_definition = trim(trim(trim(enum_definition)[len(enum_prefix):])[1:])
    enum_definition = enum_definition.replace('};','')
    entries = enum_definition.split(comma)
    for entry in entries:
        if entry != entries[0]:
            formatted_definition += comma
        formatted_definition += '\n' + enum_indent + base_indent + trim(entry)
    formatted_definition += '\n' + enum_indent + '};\n'
    return formatted_definition


def get_function(function_indent, base_indent, translation_unit, cursor, class_prefix=''):
    tokens = get_tokens(translation_unit, cursor)

    function = function_indent
    open_braces = 0
    indent = function_indent
    for i in range(len(tokens)):
        spelling = tokens[i].spelling

        if spelling == cursor.spelling:
            spelling = class_prefix + spelling
        if spelling == open_brace:
            function += '\n' + indent + spelling + '\n' + indent + base_indent
            open_braces += 1
            indent += base_indent
        elif spelling == close_brace:
            open_braces -= 1
            indent = function_indent + open_braces * base_indent
            function = function[:-len(base_indent)]
            function += spelling + '\n' + indent
            if open_braces == 0:
#                function += '\n'
                break
        elif spelling == semicolon:
            function = function[:-1]
            function += spelling + '\n' + indent
        else:
            function += spelling + ' '

    if function.endswith(indent):
        function = function[:-len(indent)]
    if function_indent == '':
        function = function[1:]
    return function


def get_function_declaration(translation_unit, cursor, class_prefix=''):
    tokens = get_tokens(translation_unit, cursor)

    function_declaration = ''
    for token in tokens:
        spelling = token.spelling
        if spelling == cursor.spelling:
            spelling = class_prefix + spelling
        if spelling == open_brace or spelling == semicolon:
            break
        elif spelling == '*' or spelling == '&':
            function_declaration = function_declaration[:-1]
            function_declaration += spelling + ' '
        elif spelling == '::':
            function_declaration = function_declaration[:-1]
            function_declaration += spelling
        else:
            function_declaration += spelling + ' '
    return function_declaration[:-1] + ';\n'


def is_inclusion_directive(kind):
    return kind == CursorKind.INCLUSION_DIRECTIVE

def is_class(kind):
    return kind == CursorKind.CLASS_DECL or \
                    kind == CursorKind.STRUCT_DECL or \
                    kind == CursorKind.CLASS_TEMPLATE or \
                    kind == CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION


def is_forward_declaration(translation_unit, cursor):
    if not is_class(cursor.kind):
        return False
    return get_class_prefix(translation_unit, cursor)[-1] == ';'


def is_namespace(kind):
    return kind == CursorKind.NAMESPACE


def is_function(kind):
    return kind == CursorKind.CXX_METHOD or \
                    kind == CursorKind.CONVERSION_FUNCTION

def is_template(kind):
    return kind == CursorKind.CLASS_TEMPLATE or \
                    kind == CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION or \
                    kind == CursorKind.FUNCTION_TEMPLATE


def is_type_alias(kind):
    return kind == CursorKind.TYPE_ALIAS_DECL


def is_typedef(kind):
    return kind == CursorKind.TYPEDEF_DECL


def is_static_or_global_variable(kind):
    return kind == CursorKind.VAR_DECL


def is_enum(kind):
    return kind == CursorKind.ENUM_DECL


def is_access_specifier(kind):
    return kind == CursorKind.CXX_ACCESS_SPEC_DECL


def is_variable(kind):
    return kind == CursorKind.FIELD_DECL


def is_member_variable(kind):
    return is_variable(kind)


def is_constructor(kind):
    return kind == CursorKind.CONSTRUCTOR


def is_destructor(kind):
    return kind == CursorKind.DESTRUCTOR


def print_function(fun):
    print "Function:"
    print 'signature: \t\t' + fun.signature
    print 'name: \t\t\t' + fun.name
    print 'arg names: \t\t' + fun.argument_names
    print 'return str: \t\t' + fun.return_str
    print 'const qualifier: \t' + fun.const_qualifier
    print ''


class SpecifierParser(object):
    def __init__(self):
        self.last = ''

    def parse(self,function,spelling):
        if spelling == '=':
            self.last = '='
        elif spelling == 'default' and last == '=':
            function.is_default = True
            self.last = ''
        elif spelling == 'delete' and last == '=':
            function.is_deleted = True
            self.last = ''
        elif spelling == 'noexcept':
            function.is_noexcept = True
            self.last = ''
        return function


def make_type(spellings):
    function_type = ''
    for spelling in spellings:
        function_type += spelling
        if spelling == 'const' or spelling == 'typename':
            function_type += ' '
    return function_type


def print_list(list):
    print "list"
    for entry in list:
        print entry


# def read_arguments(current_index,tokens):
#     arguments = []
#     counter = InTypeCounter(open_parens=1, open_brackets=0)
#     arg_tokens = []
#     while current_index < len(tokens):
#         spelling = tokens[current_index].spelling
#         counter.process(spelling)
#         if counter.open_parens == 0:
#             if len(arg_tokens) > 0:
#                 arguments.append(FunctionArgument(arg_tokens))
#             return arguments, current_index
#         if spelling == comma and counter.initial_state():
#             arguments.append(FunctionArgument(arg_tokens))
#             arg_tokens = []
#         else:
#             arg_tokens.append(tokens[current_index])
#         current_index += 1


def parse_inclusion_directive(data,cursor):
    tokens = get_tokens(data.tu, cursor)
    return tokens[0].spelling + tokens[1].spelling + ' ' + tokens[2].spelling + '\n'


my_identifier_regex = re.compile(r'[_a-zA-Z][_a-zA-Z0-9]*')
regex_for_identifier = r'[_a-zA-Z][_a-zA-Z0-9]*'
regex_for_type = regex_for_identifier + r'\s'

def get_function_regex(name):
    return re.compile( r'constexpr*\s*virtual\s*(.*)' + name + r'\s*\( .*(=*[_a-zA-Z][_a-zA-Z0-9]*)*\)\s*(const|noexcept|override|final|\&|\&\&)*\s*' )


def read_function_specifiers(function,tokens,index):
    last_was_equals = False
    while True:
        spelling = tokens[index].spelling
        if spelling == 'noexcept':
            function.is_noexcept = True
        elif spelling == 'const':
            function.is_const = True
        elif spelling == 'override':
            function.overrides_virtual = True
        elif spelling == 'final':
            function.is_final == True
        elif spelling == open_brace or spelling == semicolon:
            return function, index
        elif spelling == '=':
            last_was_equals = True
        elif last_was_equals:
            if spelling == 'default':
                function.is_default = True
            elif spelling == 'delete':
                function.is_deleted = True
            last_was_equals = False
        index += 1
#
#
# def function_data(data,cursor):
#     function_name = cursor.spelling
#     return_str = cursor.result_type.kind != TypeKind.VOID and 'return ' or ''
#
#     tokens = get_tokens(data.tu, cursor)
#     str = ''
#     constness = ''
#
#     identifier_regex = re.compile(r'[_a-zA-Z][_a-zA-Z0-9]*')
#
#     probably_args = []
#     close_paren_seen = False
#     for i in range(len(tokens)):
#         spelling = tokens[i].spelling
#         if identifier_regex.match(spelling) and i < len(tokens) - 1 and (
#                 tokens[i + 1].spelling == comma or tokens[i + 1].spelling == close_paren):
#             probably_args.append(spelling)
#         if close_paren_seen and spelling == 'const':
#             constness = 'const'
#         if spelling == close_paren:
#             close_paren_seen = True
#         if spelling == open_brace or spelling == semicolon:
#             break
#         if i:
#             str += ' '
#         str += spelling
#
#     args = [x for x in cursor.get_arguments()]
#     args_str = ''
#
#
#     for i in range(len(args)):
#         arg_cursor = args[i]
#         # Sometimes, libclang gets confused.  When it does, try our best to
#         # figure out the parameter names anyway.
#         if arg_cursor.spelling == '':
#             args_str = ', '.join(probably_args)
#             os.write(2,
#                      '''An error has occurred in determining the name of parameter {} of function
#                      {}. This usually occurs when libclang can't figure out the type of the
#                      parameter (often due to a typo or missing include somewhere).  We're using
#                      these possibly-wrong, heuristically-determined parameter names instead:
#                      '{}'.\n'''.format(i, function_name, args_str))
#             break
#         if i:
#             args_str += ', '
#         args_str += arg_cursor.spelling
#
#     return Function( function_name, str, args_str, return_str, constness == 'const')
