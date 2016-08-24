#!/usr/bin/env python

import argparse
import code
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
from inheritance_based_file_writer import HeaderOnlyInterfaceFileWriter
from inheritance_based_file_writer import InterfaceFileWriter
from file_writer import get_source_filename
from vtable_based_file_writer import HeaderOnlyVTableInterfaceFileWriter
from vtable_based_file_writer import VTableInterfaceFileWriter
import file_parser
import cpp_file_parser
import to_string
import util


def add_arguments(parser):
    parser.add_argument('--interface-file', type=str, required=False, help='write output to given file')
    parser.add_argument('-cow', '--copy-on-write', nargs='?', type=str, required=False,
                        const=True, default=False)
    parser.add_argument('--headers', type=str, required=False,
                        help='file containing headers to prepend to the generated code')
    parser.add_argument('--header-only', action='store_true',
                        help='disables generation of source files')
    parser.add_argument('--buffer', nargs='?', type=str, required=False,
                        default='128',
                        help='buffer size or c++-macro specifying the buffer size')
    parser.add_argument('-sbo', '--small-buffer-optimization', nargs='?', type=bool, required=False,
                        const=True, default=False,
                        help='enables small buffer optimization')


def create_parser():
    parser = argparse.ArgumentParser(description='Generates interface for type-erased C++ code.')
    add_default_arguments(parser)
    add_arguments(parser)
    return parser


def parse_additional_args(args, data):
    data.interface_file = args.interface_file
    data.interface_form_lines = util.prepare_form(open(args.interface_form).readlines())
    data.headers = args.headers and open(args.headers).read() or ''
    data.copy_on_write = args.copy_on_write
    data.header_only = args.header_only
    data.buffer = args.buffer
    data.small_buffer_optimization = args.small_buffer_optimization
    if not data.header_only:
        data.interface_cpp_form_lines = util.prepare_form(open(args.interface_form.replace('.hpp','.cpp')).readlines())

    return data


def parse_args(args):
    data = util.client_data()
    data = util.parse_default_args(args, data)
    data = parse_additional_args(args, data)
    data.buffer = args.buffer
    return data


def get_filewriter(data, indentation, comments):
    if data.vtable:
        if data.header_only:
            return HeaderOnlyVTableInterfaceFileWriter(data.interface_file, indentation, comments)
        return VTableInterfaceFileWriter(data.interface_file, get_source_filename(data.interface_file), indentation, comments)
    else:
        if data.header_only:
            return HeaderOnlyInterfaceFileWriter(data.interface_file, indentation, comments)
        return InterfaceFileWriter(data.interface_file, get_source_filename(data.interface_file), indentation, comments)


def add_default_interface(scope, classname, detail_namespace):
    scope.add( cpp_file_parser.get_function_from_text(classname, classname, '',
                                                      code.get_default_default_constructor(classname,'noexcept','constexpr'),
                                                      'constructor') )
    scope.add(cpp_file_parser.get_function_from_text(classname, classname, '',
                                                     code.get_handle_constructor(classname, detail_namespace),
                                                     'constructor'))
    scope.add(cpp_file_parser.get_function_from_text(classname, classname, '',
                                                     code.get_handle_copy_constructor(classname),
                                                     'constructor'))
    scope.add( cpp_file_parser.get_function_from_text(classname, classname, '',
                                                      code.get_handle_move_constructor(classname),
                                                      'constructor') )
    scope.add( cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                      code.get_handle_assignment(classname, detail_namespace) ) )
    scope.add( cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                      code.get_handle_copy_operator(classname) ) )
    scope.add( cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                      code.get_handle_move_operator(classname) ) )
    scope.add( cpp_file_parser.get_function_from_text(classname, 'operator bool', 'return ',
                                                      code.get_operator_bool_for_member_ptr('handle_') ) )
    scope.add( cpp_file_parser.get_function_from_text(classname, 'target', 'return ',
                                                      code.get_handle_cast('handle_', detail_namespace) ) )
    scope.add( cpp_file_parser.get_function_from_text(classname, 'target', 'return ',
                                                      code.get_handle_cast('handle_', detail_namespace, 'const') ) )


def add_pimpl(scope, detail_namespace):
    scope.add(cpp_file_parser.AccessSpecifier('private'))
    scope.add(cpp_file_parser.Variable('std::unique_ptr< ' + detail_namespace + '::HandleBase > handle_;'))

def add_interface(scope, class_scope, detail_namespace):
    if util.is_class(class_scope):
        scope.add(cpp_file_parser.Class(class_scope.get_name()))
        scope.add(cpp_file_parser.AccessSpecifier('public'))
    else:
        scope.add(cpp_file_parser.Struct(class_scope.get_name()))

    add_default_interface(scope, class_scope.get_name(), detail_namespace)


    is_private = util.is_class(class_scope)
    for entry in class_scope.content:
        if cpp_file_parser.is_access_specifier(entry):
            is_private = entry.value == cpp_file_parser.PRIVATE
        elif not is_private:
            if cpp_file_parser.is_function(entry):
                scope.add(cpp_file_parser.get_function_from_text(class_scope.get_name(), entry.name, entry.return_str,
                                                                 code.get_handle_interface_function(entry)))
            else:
                scope.add(entry)




#    destructor = 'virtual ~ ' + classname + ' ( ) = default ;'
#    add_function(scope, classname, '~'+classname, '', destructor, 'destructor')
#    clone = 'virtual ' + classname + ' * clone ( ) const = 0 ;'
#    add_function(scope, classname, 'clone', 'return ', clone)

    # for entry in class_scope.content:
    #     if util.is_function(entry):
    #         tokens = copy.deepcopy(entry.tokens[:cpp_file_parser.get_declaration_end_index(entry.name,entry.tokens)])
    #
    #         if tokens[0].spelling != 'virtual':
    #             tokens.insert(0,cpp_file_parser.SimpleToken('virtual'))
    #
    #         if tokens[-1].spelling != '0' or tokens[-2].spelling != '=':
    #             tokens.extend([cpp_file_parser.SimpleToken('='),
    #                            cpp_file_parser.SimpleToken('0')])
    #         tokens.append(cpp_file_parser.SimpleToken(';'))
    #
    #         scope.add( cpp_file_parser.Function(entry.classname, entry.name, entry.return_str, tokens) )

    add_pimpl(scope, detail_namespace)
    scope.close()


def get_basic_interface_file_impl(data, scope, interface_scope):
    for entry in interface_scope.content:
        if util.is_namespace(entry):
            scope.add(cpp_file_parser.Namespace(entry.name))
            get_basic_interface_file_impl(data, scope, entry)
            scope.close()
        elif util.is_class(entry) or util.is_struct(entry):
            add_interface(scope, entry, entry.name + data.detail_extension)
        else:
            scope.add(entry)


def get_basic_interface_file(data, interface_scope):
    main_scope = cpp_file_parser.Namespace('global')
    main_scope.add( cpp_file_parser.InclusionDirective('"handles/handle_for_' + data.interface_file + '"') )
    get_basic_interface_file_impl(data, main_scope, interface_scope)
    return main_scope


def write_file(args):
    data = parse_args(args)
    processor = cpp_file_parser.CppFileParser()
    parser = file_parser.GenericFileParser(processor, data)
    parser.parse()

    scope = get_basic_interface_file(data, processor.content)
    to_string.write_scope(scope, data.interface_file)
    util.clang_format(data.interface_file)

# def write_file2(args, indentation):
#     if args.header_only:
#         args.interface_form = args.interface_form.replace('.hpp','_header_only.hpp')
#     data = parse_args(args)
#     comments = extract_comments(data.file)
#
#     interface_headers = extract_includes(data.file)
#     interface_headers.append('#include "' + args.handle_file + '"')
#
#     file_writer = get_filewriter(data, indentation, comments)
#     file_writer.process_open_include_guard(args.file)
#     file_writer.process_headers(interface_headers)
#
#     file_parser = GenericFileParser(file_writer,data)
#     file_parser.parse()
#
#     file_writer.process_close_include_guard()
#     file_writer.write_to_file()


# main
if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    indentation = ' ' * args.indent

    write_file(args,indentation)

