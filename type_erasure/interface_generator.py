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
from file_writer import HeaderOnlyInterfaceFileWriter
from file_writer import InterfaceFileWriter
from file_writer import InterfaceHeaderFileWriter
from file_writer import InterfaceSourceFileWriter
from file_writer import get_source_filename
from file_parser import GenericFileParser


def add_arguments(parser):
    parser.add_argument('--interface-file', type=str, required=False, help='write output to given file')
    parser.add_argument('-cow', '--copy-on-write', nargs='?', type=str, required=False,
                        const=True, default=False)
#    parser.add_argument('--interface-form', type=str, required=True,
#                        help='form used to generate code for the type-erased interface (constructors, assignment operators, ...)')
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
    data.interface_form_lines = prepare_form(open(args.interface_form).readlines())
    data.headers = args.headers and open(args.headers).read() or ''
    data.copy_on_write = args.copy_on_write
    data.header_only = args.header_only
    data.buffer = args.buffer
    data.small_buffer_optimization = args.small_buffer_optimization
    if not data.header_only:
        data.interface_cpp_form_lines = prepare_form(open(args.interface_form.replace('.hpp','.cpp')).readlines())

    return data


def parse_args(args):
    data = client_data()
    data = parse_default_args(args, data)
    data = parse_additional_args(args, data)
    data.buffer = args.buffer
    return data


def get_filewriter(data, indentation, comments):
    if data.header_only:
        return HeaderOnlyInterfaceFileWriter(data.interface_file, indentation, data.handle_namespace, comments)
    return InterfaceFileWriter(data.interface_file, get_source_filename(data.interface_file), indentation, data.handle_namespace, comments)


def write_file(args, indentation):
    if args.header_only:
        args.interface_form = args.interface_form.replace('.hpp','_header_only.hpp')
    data = parse_args(args)
    comments = extract_comments(data.file)

    interface_headers = extract_includes(data.file)
    interface_headers.append('#include "' + args.handle_file + '"')

    file_writer = get_filewriter(data, indentation, comments)
    file_writer.process_open_include_guard(args.file)
    file_writer.process_headers(interface_headers)

    file_parser = GenericFileParser(file_writer,data)
    file_parser.parse()

    file_writer.process_close_include_guard()
    file_writer.write_to_file()


# main
if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    indentation = ' ' * args.indent

    write_file(args,indentation)

