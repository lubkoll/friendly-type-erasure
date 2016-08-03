#!/usr/bin/env python


import argparse
import os
import re
import sys
from clang.cindex import Config
from clang.cindex import CursorKind
from clang.cindex import TypeKind
from clang.cindex import TranslationUnit
from parser_addition import trim
from parser_addition import extract_comments
from parser_addition import extract_includes
from util import *


def add_arguments(parser):
    parser.add_argument('--interface-file', type=str, required=False, help='write output to given file')
    parser.add_argument('-cow', '--copy-on-write', nargs='?', type=str, required=False,
                        const=True, default=False)
#    parser.add_argument('--interface-form', type=str, required=True,
#                        help='form used to generate code for the type-erased interface (constructors, assignment operators, ...)')
    parser.add_argument('--headers', type=str, required=False,
                        help='file containing headers to prepend to the generated code')


def create_parser():
    parser = argparse.ArgumentParser(description='Generates interface for type-erased C++ code.')
    add_default_arguments(parser)
    add_arguments(parser)
    return parser


def parse_additional_args(args, data):
    data.interface_file = args.interface_file
    data.interface_form = prepare_form(open(args.interface_form).read())
    data.interface_form_lines = prepare_form(open(args.interface_form).readlines())
    data.headers = args.headers and open(args.headers).read() or ''
    data.copy_on_write = args.copy_on_write
    return data


def parse_args(args):
    data = client_data()
    data = parse_default_args(args, data)
    data = parse_additional_args(args, data)
    data = parse_file(args, data)
    return data


def member_params (data,cursor):
    tokens = get_tokens(data.tu, cursor)

    open_brace = '{'
    semicolon = ';'
    close_paren = ')'
    const_token = 'const'
    comma = ','

    str = ''
    constness = ''

    identifier_regex = re.compile(r'[_a-zA-Z][_a-zA-Z0-9]*')

    probably_args = []
    close_paren_seen = False
    for i in range(len(tokens)):
        spelling = tokens[i].spelling
        if identifier_regex.match(spelling) and i < len(tokens) - 1 and (tokens[i + 1].spelling == comma or tokens[i + 1].spelling == close_paren):
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


def find_expansion_lines (lines):
    retval = [0] * 3
    for i in range(len(lines)):
        line = lines[i]
        try:
            nonvirtual_pos = line.index('{nonvirtual_members}')
        except:
            nonvirtual_pos = -1
        try:
            pure_virtual_pos = line.index('{pure_virtual_members}')
        except:
            pure_virtual_pos = -1
        try:
            virtual_pos = line.index('{virtual_members}')
        except:
            virtual_pos = -1
        if nonvirtual_pos != -1:
            retval[0] = (i, nonvirtual_pos)
        elif pure_virtual_pos != -1:
            retval[1] = (i, pure_virtual_pos)
        elif virtual_pos != -1:
            retval[2] = (i, virtual_pos)
    return retval

def close_struct (data, comments, indentation):
    lines = data.interface_form_lines

    expansion_lines = find_expansion_lines(lines)
    class_indent = ''
    base_indent = class_indent + indentation
    indent = base_indent + indentation

    comment = get_comment(class_indent,comments,data.current_struct_prefix).rstrip('\n\r')
    
    lines = map(
        lambda line: line.format(
            struct_prefix=comment + data.current_struct_prefix,
            struct_name=data.current_struct.spelling,
            nonvirtual_members='{nonvirtual_members}',
        ),
        lines
    )

    nonvirtual_members = ''

    for function in data.member_functions:
        nonvirtual_members += get_comment(base_indent, comments, function[0])
        nonvirtual_members += \
            base_indent + function[0] + '\n' + \
            base_indent + '{\n' + \
            indent + 'assert(handle_);\n' + \
            indent + function[2]
        if data.copy_on_write:
            nonvirtual_members += ( function[4] == 'const' and 'read().' or 'write().')
        else:
            nonvirtual_members += 'handle_->'
        nonvirtual_members += function[3] + '(' + function[1] + ' );\n' + \
            base_indent + '}\n'
        if not function is data.member_functions[-1]:
            nonvirtual_members += '\n'

    nonvirtual_members = nonvirtual_members[:-1]

    lines[expansion_lines[0][0]] = nonvirtual_members

    return lines



def write_interface_to_file_impl (data, file, cursor, parent, comments, indentation):
    try:
        kind = cursor.kind
    except:
        return child_visit.Break

    indent = ''
    # close open namespaces we have left
    enclosing_namespace = parent
    while enclosing_namespace != data.tu.cursor and not is_namespace(enclosing_namespace.kind):
        enclosing_namespace = enclosing_namespace.semantic_parent

    if enclosing_namespace != data.tu.cursor and is_namespace(enclosing_namespace.kind):
        while len(data.current_namespaces) and \
              enclosing_namespace != data.current_namespaces[-1]:
            data.current_namespaces.pop()
            close_namespace(file, indent)
            indent *= 0
            indent += (len(data.current_namespaces) - 1) * indentation

    # close open struct if we have left it
    enclosing_struct = parent
    while enclosing_struct and \
          enclosing_struct != data.tu.cursor and \
          not is_class(enclosing_struct.kind):
        enclosing_struct = enclosing_struct.semantic_parent

    if enclosing_struct and \
       data.current_struct != clang.cindex.conf.lib.clang_getNullCursor() and \
       enclosing_struct != data.current_struct:
        close_struct(data,comments,indentation)
        data.current_struct = clang.cindex.conf.lib.clang_getNullCursor()
        data.member_functions = []

    location = cursor.location
    from_main_file_ = clang.cindex.conf.lib.clang_Location_isFromMainFile(location)

    kind = cursor.kind
    if is_namespace(kind):
        if from_main_file_:
            open_namespace(file, cursor.spelling, indent)
            data.current_namespaces.append(cursor)
            indent *= 0
            indent += (len(data.current_namespaces) - 1) * indentation
        return child_visit.Recurse
    elif not from_main_file_:
        return child_visit.Continue
    elif is_class(kind):
        if data.current_struct == clang.cindex.conf.lib.clang_getNullCursor():
            data.current_struct = cursor
            data.current_struct_prefix = class_prefix(data.tu,cursor)
            return child_visit.Recurse
    elif is_function(kind):
        data.member_functions.append(member_params(data,cursor))

    return child_visit.Continue


def write_interface_to_file (data, file, cursor, comments, indentation):
    for child in cursor.get_children():
        result = write_interface_to_file_impl(data, file, child, cursor, comments, indentation)
        if result == child_visit.Recurse:
            if write_interface_to_file(data, file, child, comments, indentation) == child_visit.Break:
                return child_visit.Break
        elif result == child_visit.Break:
            return child_visit.Break
        elif result == child_visit.Continue:
            continue


def write_file(args, indentation, impl_namespace_name=''):

    data = parse_args(args)
    comments = extract_comments(data.filename)
    interface_headers = extract_includes(data.filename)

    file = open(args.interface_file,'w')
    include_guard = add_include_guard(file,data.filename,comments)
    add_headers(file,interface_headers)
    file.write('#include "' + args.handle_file + '"\n\n')

    write_interface_to_file(data, file, data.tu.cursor, comments, indentation)

    if data.current_struct != clang.cindex.conf.lib.clang_getNullCursor():
        code = close_struct(data,comments,indentation)

    base_indent = len(data.current_namespaces) * indentation
    for entry in code:
        lines = entry.split('\n')
        for line in lines:
            if impl_namespace_name != '':
                line = line.replace(' Handle', ' ' + impl_namespace_name + '::Handle')
                line = line.replace('(Handle', '(' + impl_namespace_name + '::Handle')
                line = line.replace('<Handle', '<' + impl_namespace_name + '::Handle')
            file.write(base_indent + line + '\n')

    close_namespaces(file, data, indentation)
    close_include_guard(file, include_guard)
    file.write('\n')
    file.close()

# main
if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    indentation = ' ' * args.indent

    write_file(args,indentation)

