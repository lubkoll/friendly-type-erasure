#!/usr/bin/env python

import argparse
import clang
from util import add_default_arguments, close_namespaces, parse_default_args, client_data, prepare_form
from parser_addition import extract_includes
from file_writer import HandleFileWriter
from file_parser import GenericFileParser


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
    return data


def write_file(args, indentation):
    data = parse_args(args)

    file_writer = HandleFileWriter(data.handle_file, indentation)
    file_writer.process_open_include_guard(args.file)
    file_writer.process_headers(extract_includes(args.handle_headers))

    file_parser = GenericFileParser(file_writer,data)
    file_parser.parse()

    file_writer.process_close_include_guard()
    file_writer.write_to_file()

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    indentation = ' ' * args.indent

    write_file(args,indentation)
