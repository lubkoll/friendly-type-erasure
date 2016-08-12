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
    return parser

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


def get_handle_form(args):
    if args.vtable:
        if args.copy_on_write and args.small_buffer_optimization:
            return os.path.join(os.path.dirname(__file__), 'forms', 'vtable_based', 'sbo_cow', 'execution_wrapper.hpp')
        elif args.copy_on_write and not args.small_buffer_optimization:
            return os.path.join(os.path.dirname(__file__), 'forms', 'vtable_based', 'cow', 'execution_wrapper.hpp')
        elif not args.copy_on_write and args.small_buffer_optimization:
            return os.path.join(os.path.dirname(__file__), 'forms', 'vtable_based', 'sbo', 'execution_wrapper.hpp')
        else:
            return os.path.join(os.path.dirname(__file__), 'forms', 'vtable_based', 'basic', 'execution_wrapper.hpp')
    else:
        if args.copy_on_write and args.small_buffer_optimization:
            return os.path.join(os.path.dirname(__file__), 'forms', 'inheritance_based', 'sbo_cow', 'handle_form.hpp')
        elif args.copy_on_write and not args.small_buffer_optimization:
            return os.path.join(os.path.dirname(__file__), 'forms', 'inheritance_based', 'cow', 'handle_form.hpp')
        elif not args.copy_on_write and args.small_buffer_optimization:
            return os.path.join(os.path.dirname(__file__), 'forms', 'inheritance_based', 'sbo', 'handle_form.hpp')
        else:
            return os.path.join(os.path.dirname(__file__), 'forms', 'inheritance_based', 'basic', 'handle_form.hpp')


def get_inheritance_based_interface_form(args):
    if args.copy_on_write and args.small_buffer_optimization:
        return os.path.join(os.path.dirname(__file__), 'forms', 'inheritance_based', 'sbo_cow', 'form.hpp')
    elif args.copy_on_write and not args.small_buffer_optimization:
        return os.path.join(os.path.dirname(__file__), 'forms', 'inheritance_based', 'cow', 'form.hpp')
    elif not args.copy_on_write and args.small_buffer_optimization:
        return os.path.join(os.path.dirname(__file__), 'forms', 'inheritance_based', 'sbo', 'form.hpp')
    else:
        return os.path.join(os.path.dirname(__file__), 'forms', 'inheritance_based', 'basic', 'form.hpp')


def get_vtable_based_interface_form(args):
    if args.copy_on_write and args.small_buffer_optimization:
        return os.path.join(os.path.dirname(__file__), 'forms', 'vtable_based', 'sbo_cow', 'form.hpp')
    elif args.copy_on_write and not args.small_buffer_optimization:
        return os.path.join(os.path.dirname(__file__), 'forms', 'vtable_based', 'cow', 'form.hpp')
    elif not args.copy_on_write and args.small_buffer_optimization:
        return os.path.join(os.path.dirname(__file__), 'forms', 'vtable_based', 'sbo', 'form.hpp')
    else:
        return os.path.join(os.path.dirname(__file__), 'forms', 'vtable_based', 'basic', 'form.hpp')


def get_interface_form(args):
    if args.vtable:
        return get_vtable_based_interface_form(args)
    else:
        return get_inheritance_based_interface_form(args)


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

    if args.vtable:
        call(["cp", os.path.join(os.path.dirname(__file__), 'forms', 'vtable_based', 'vtable_util.hh'), args.handle_folder])
    else:
        call(["cp", os.path.join(os.path.dirname(__file__), 'forms', 'inheritance_based', 'util.hh'), args.handle_folder])

    if args.vtable:
        if args.copy_on_write:
            args.handle_headers = os.path.join(os.path.dirname(__file__), 'headers', 'vtable_cow.hpp')
        else:
            args.handle_headers = os.path.join(os.path.dirname(__file__), 'headers', 'vtable.hpp')
    else:
        if args.copy_on_write and args.small_buffer_optimization:
            args.handle_headers = os.path.join(os.path.dirname(__file__), 'headers', 'sbo_cow_handle.hpp')
        else:
            args.handle_headers = os.path.join(os.path.dirname(__file__), 'headers', 'handle.hpp')
    args.handle_form = get_handle_form(args)
    args.interface_form = get_interface_form(args)

    indentation = ' ' * args.indent

    impl_namespace_name = type_erasure.handle_generator.write_file(args,indentation)
    type_erasure.interface_generator.write_file(args,indentation)
