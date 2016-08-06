import argparse
import clang
from subprocess import call
import os
import sys
import type_erasure.file_parser
import type_erasure.handle_generator
import type_erasure.interface_generator
from type_erasure.util import add_default_arguments
from clang.cindex import Config


def create_parser():
    parser = argparse.ArgumentParser(description='Generates handles for type-erased C++ code.')
    add_default_arguments(parser)
    type_erasure.handle_generator.add_arguments(parser)
    type_erasure.interface_generator.add_arguments(parser)
    parser.add_argument('--handle-folder', nargs='?', type=str, required=False,
                        default='handles',
                        help='folder for handle implementations')
#    parser.add_argument('-cow', '--copy-on-write', nargs='?', type=bool, required=False,
#                        const=True, default=False,
#                        help='enables copy on write')
    return parser

def absolute_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)

class client_data:
    def __init__(self):
        self.tu = None
        self.current_namespaces = []  # cursors
        self.current_struct = clang.cindex.conf.lib.clang_getNullCursor()
        # function signature, forwarding call arguments, optional return
        # keyword, function name, and "const"/"" for function constness
        self.member_functions = []  # each element [''] * 5
        self.filename = ''
        self.handle_form = ''
        self.handle_file = ''
        self.interface_form = ''
        self.interface_file = ''
        self.form_lines = []
        self.non_copyable = False
        self. indent = ''
        self.impl_ending = ''


def parse_args(args):
    data = client_data()
    data = parse_default_args(args, data)
    data = type_erasure.handle_generator.parse_additional_args(args, data)
    data = type_erasure.interface_generator.parse_additional_args(args, data)
    data = parse_file(args, data)
    data.header_only = args.header_only
    return data


def get_handle_from(args):
    if not args.copy_on_write and not args.small_buffer_optimization:
        return absolute_path('forms/basic_handle.hpp')
    elif args.copy_on_write and not args.small_buffer_optimization:
        return absolute_path('forms/cow_handle.hpp')
    elif not args.copy_on_write and args.small_buffer_optimization:
       return absolute_path('forms/sbo_handle.hpp')
    else:
        return absolute_path('forms/sbo_cow_handle.hpp')


def get_interface_form(args):
    if args.copy_on_write and args.small_buffer_optimization:
        return absolute_path('forms/sbo_cow.hpp')
    elif args.copy_on_write and not args.small_buffer_optimization:
        return absolute_path('forms/cow.hpp')
    elif not args.copy_on_write and args.small_buffer_optimization:
        return absolute_path('forms/sbo.hpp')
    else:
        return absolute_path('forms/basic.hpp')


class NamespaceNamesExtractor(type_erasure.file_parser.FileProcessor):
    def __init__(self,extension):
        self.extension = extension
        self.namespace_names = []

    def process_open_class(self, data):
        self.namespace_names.append(data.current_struct.spelling + self.extension)

class ExtractorData:
    def __init__(self):
        self.tu = None
        self.current_namespaces = []  # cursors
        self.current_struct = clang.cindex.conf.lib.clang_getNullCursor()
        self.file = None
        self.clang_args = None

def get_handle_namespace_name(args):
    if args.handle_namespace != '':
        return args.handle_namespace

    namespace_name_extractor = NamespaceNamesExtractor(args.handle_extension)
    data = ExtractorData()
    data.file = args.file
    data.clang_args = args.clang_args
    parser = type_erasure.file_parser.GenericFileParser(namespace_name_extractor, data)
    parser.parse()
    return namespace_name_extractor.namespace_names[0]

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)
    args.handle_namespace = get_handle_namespace_name(args)

    call(["cp", absolute_path("forms/util.hh"), args.handle_folder + "/"])

    if args.copy_on_write and args.small_buffer_optimization:
        args.handle_headers = absolute_path('headers/sbo_cow_handle.hpp')
    else:
        args.handle_headers = absolute_path('headers/handle.hpp')
    args.handle_form = get_handle_from(args)
    args.interface_form = get_interface_form(args)

    indentation = ' ' * args.indent

    impl_namespace_name = type_erasure.handle_generator.write_file(args,indentation)
    type_erasure.interface_generator.write_file(args,indentation)
