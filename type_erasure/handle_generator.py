#!/usr/bin/env python


import argparse
import os
import re
import sys
from clang.cindex import Config
from clang.cindex import CursorKind
from clang.cindex import TypeKind
from clang.cindex import TranslationUnit
from util import *
from parser_addition import extract_includes


def add_arguments(parser):
#    parser.add_argument('--handle-form', type=str, required=True,
#                        help='form used to generate code for handles')
    parser.add_argument('--handle-file', type=str, required=False, help='write output to given file')
#    parser.add_argument('--handle-headers', type=str, required=False, help='headers for the handle file',
#                        default='')


def create_parser():
    parser = argparse.ArgumentParser(description='Generates handles for type-erased C++ code.')
    add_default_arguments(parser)
    add_arguments(parser)
    return parser


def parse_additional_args(args,data):
    data.handle_form = prepare_form(open(args.handle_form).read())
    data.handle_form_lines = prepare_form(open(args.handle_form).readlines())
    data.handle_file = args.handle_file
    return data


def parse_args(args):
    data = client_data()
    data = parse_default_args(args,data)
    data = parse_additional_args(args,data)
    data = parse_file(args, data)
    return data


def member_params(data,cursor):
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
        if close_paren_seen and spelling == const_token:
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

    function_name = cursor.spelling

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

    return_str = cursor.result_type.kind != TypeKind.VOID and 'return ' or ''

    return [str, args_str, return_str, function_name, constness]


def find_expansion_lines(lines):
    retval = [0] * 3
    for i in range(len(lines)):
        line = lines[i]
        try:
            namespace_prefix_pos = line.index('{namespace_prefix}')
        except:
            namespace_prefix_pos = -1
        try:
            pure_virtual_pos = line.index('{pure_virtual_members}')
        except:
            pure_virtual_pos = -1
        try:
            virtual_pos = line.index('{virtual_members}')
        except:
            virtual_pos = -1
        if namespace_prefix_pos != -1:
            retval[0] = (i, namespace_prefix_pos)
        elif pure_virtual_pos != -1:
            retval[1] = (i, pure_virtual_pos)
        elif virtual_pos != -1:
            retval[2] = (i, virtual_pos)
    return retval


def close_struct(data,indentation):
    lines = data.handle_form_lines

    expansion_lines = find_expansion_lines(lines)
    base_indent = (len(data.current_namespaces) + 1) * indentation
    indent = base_indent + indentation

    lines = map(
        lambda line: line.format(
            struct_name=data.current_struct.spelling,
            namespace_prefix='{namespace_prefix}',
            pure_virtual_members='{pure_virtual_members}',
            virtual_members='{virtual_members}'
        ),
        lines
    )

    pure_virtual_members = ''
    virtual_members = ''

    for function in data.member_functions:
        if pure_virtual_members == '':
            pure_virtual_members += base_indent
        else:
            pure_virtual_members += indent
        pure_virtual_members += \
            'virtual ' + function[0] + ' = 0;\n'

        if virtual_members == '':
            virtual_members += base_indent
        else:
            virtual_members += indent
        virtual_members += \
            'virtual ' + function[0] + ' override\n' + \
            indent + '{\n' + \
            indent + indentation + function[2] + \
            'value_.' + function[3] + \
            '(' + function[1] + ' );\n' + \
            indent + '}\n'
        if function is data.member_functions[-1]:
            pass
        else:
            virtual_members += '\n'

    pure_virtual_members = pure_virtual_members[:-1]
    virtual_members = virtual_members[:-1]

    impl_namespace_name = data.current_struct.spelling + data.impl_ending
    lines[expansion_lines[0][0]] = "namespace " + impl_namespace_name
    lines[expansion_lines[1][0]] = pure_virtual_members
    lines[expansion_lines[2][0]] = virtual_members

    return lines, impl_namespace_name


def write_handle_to_file_impl(handle_file, data, cursor, parent, indentation):
    try:
        kind = cursor.kind
    except:
        return child_visit.Break

    indent = (len(data.current_namespaces)-1)*indentation
    # close open namespaces we have left
    enclosing_namespace = parent
    while enclosing_namespace != data.tu.cursor and not is_namespace(enclosing_namespace.kind):
        enclosing_namespace = enclosing_namespace.semantic_parent

    if enclosing_namespace != data.tu.cursor and is_namespace(enclosing_namespace.kind):
        while len(data.current_namespaces) and \
                        enclosing_namespace != data.current_namespaces[-1]:
            data.current_namespaces.pop()
            close_namespace(handle_file, indent)
            indent = (len(data.current_namespaces) - 1) * indentation

    # close open struct if we have left it
    enclosing_struct = parent
    while enclosing_struct and \
                    enclosing_struct != data.tu.cursor and \
            not is_class(enclosing_struct.kind):
        enclosing_struct = enclosing_struct.semantic_parent

    if enclosing_struct and \
                    data.current_struct != clang.cindex.conf.lib.clang_getNullCursor() and \
                    enclosing_struct != data.current_struct:
        (data,handle_file,indent)
        data.current_struct = clang.cindex.conf.lib.clang_getNullCursor()
        data.member_functions = []

    location = cursor.location
    from_main_file_ = clang.cindex.conf.lib.clang_Location_isFromMainFile(location)

    kind = cursor.kind
    if is_namespace(kind):
        if from_main_file_:
            open_namespace(handle_file, cursor.spelling, indent)
            data.current_namespaces.append(cursor)
            indent = (len(data.current_namespaces) - 1) * indentation
        return child_visit.Recurse
    elif not from_main_file_:
        return child_visit.Continue
    elif is_class(kind):
        if data.current_struct == clang.cindex.conf.lib.clang_getNullCursor():
            data.current_struct = cursor
            return child_visit.Recurse
    elif is_function(kind):
        data.member_functions.append(member_params(data,cursor))

    return child_visit.Continue


def write_handle_to_file(handle_file, data, cursor, indentation=''):
    for child in cursor.get_children():
        result = write_handle_to_file_impl(handle_file, data, child, cursor, indentation)
        if result == child_visit.Recurse:
            if write_handle_to_file(handle_file, data, child, indentation) == child_visit.Break:
                return child_visit.Break
        elif result == child_visit.Break:
            return child_visit.Break
        elif result == child_visit.Continue:
            continue


def write_file(args, indentation):

    data = parse_args(args)
    handle_file = open(data.handle_file,'w')
    include_guard = add_include_guard(handle_file,args.handle_form)
    if args.handle_headers != '':
        add_headers(handle_file, extract_includes(args.handle_headers))

    write_handle_to_file(handle_file, data, data.tu.cursor, indentation)

    if data.current_struct != clang.cindex.conf.lib.clang_getNullCursor():
        lines, impl_namespace_name = close_struct(data,indentation)

    for line in lines:
        if trim(include_guard) not in line:
            handle_file.write(indentation + line + '\n')

    close_namespaces(handle_file, data, indentation)
    close_include_guard(handle_file, include_guard)
    handle_file.write('\n')
    handle_file.close()
    return impl_namespace_name

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    indentation = ' ' * args.indent

    write_file(args,indentation)
