import clang
import re

from clang.cindex import CursorKind
from clang.cindex import TypeKind


semicolon = ';'
close_paren = ')'
const_token = 'const'
open_brace = '{'
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
        if spelling == open_brace:
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
    type_alias = ''
    for token in tokens:
        spelling = token.spelling
        if token == tokens[-1]:
            type_alias += spelling + '\n'
        elif without_spaces(spelling):
            alias_start = (len(type_alias) > 0 and type_alias[:-1] or '')
            type_alias = alias_start + spelling
        elif token == tokens[-2]:
            if type_alias[-2] != ' ':
                type_alias += ' '
            type_alias += spelling
        else:
            type_alias += spelling + ' '
    return type_alias


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


def print_function(fun):
    print "Function:"
    print 'signature: \t\t' + fun.signature
    print 'name: \t\t\t' + fun.name
    print 'arg names: \t\t' + fun.argument_names
    print 'return str: \t\t' + fun.return_str
    print 'const qualifier: \t' + fun.const_qualifier
    print ''


class Function(object):
    def __init__(self, name, signature, argument_names, return_str, is_const, ):
        self.name = name
        self.signature = signature
        self.argument_names = argument_names
        self.return_str = return_str
        self.is_const = is_const
        self.const_qualifier = (is_const and 'const ' or '')


def function_data(data,cursor):
    function_name = cursor.spelling
    return_str = cursor.result_type.kind != TypeKind.VOID and 'return ' or ''

    tokens = get_tokens(data.tu, cursor)

    str = ''
    constness = ''

    identifier_regex = re.compile(r'[_a-zA-Z][_a-zA-Z0-9]*')

    probably_args = []
    close_paren_seen = False
    for i in range(len(tokens)):
        spelling = tokens[i].spelling
        if identifier_regex.match(spelling) and i < len(tokens) - 1 and (
                tokens[i + 1].spelling == comma or tokens[i + 1].spelling == close_paren):
            probably_args.append(spelling)
        if close_paren_seen and spelling == 'const':
            constness = 'const'
        if spelling == close_paren:
            close_paren_seen = True
        if spelling == open_brace or spelling == semicolon:
            break
        if i:
            str += ' '
        str += spelling

    args = [x for x in cursor.get_arguments()]
    args_str = ''


    for i in range(len(args)):
        arg_cursor = args[i]
        # Sometimes, libclang gets confused.  When it does, try our best to
        # figure out the parameter names anyway.
        if arg_cursor.spelling == '':
            args_str = ', '.join(probably_args)
            os.write(2,
                     '''An error has occurred in determining the name of parameter {} of function
                     {}. This usually occurs when libclang can't figure out the type of the
                     parameter (often due to a typo or missing include somewhere).  We're using
                     these possibly-wrong, heuristically-determined parameter names instead:
                     '{}'.\n'''.format(i, function_name, args_str))
            break
        if i:
            args_str += ', '
        args_str += arg_cursor.spelling

    return Function( function_name, str, args_str, return_str, constness == 'const')
