import argparse
import clang
from clang.cindex import Config
from subprocess import call
import os
import type_erasure.detail_generator
import type_erasure.interface_generator
import type_erasure.util


def create_parser():
    parser = argparse.ArgumentParser(description='Generates handles for type-erased C++ code.')
    parser.add_argument('--non-copyable', action='store_true',
                        help='set to true to generate a non-copyable interface (TODO)')
    parser.add_argument('--detail-extension', nargs='?', type=str,
                        default='Handles',
                        help='ending for namespace containing the handle or function pointer table implementation (not considered if --detail-namespace is specified)')
    parser.add_argument('--clang-path', type=str, required=False,
                        default='/usr/lib/llvm-3.8/lib',
                        help='path to libclang library')
    parser.add_argument('clang_args', metavar='Clang-arg', type=str, nargs=argparse.REMAINDER,
                        default='[-std=c++14]',
                        help='additional args to pass to Clang')
    parser.add_argument('file', type=str, help='the input file containing archetypes')
    parser.add_argument('--detail-namespace', nargs='?', type=str, required=False,
                        default='',
                        help='namespace containing implementations of handles, resp tables for the function pointers')
    parser.add_argument('--table', action='store_true',
                        help='use function-pointer-table-based type erasure')
    parser.add_argument('-cow', '--copy-on-write', nargs='?', type=str, required=False,
                        const=True, default=False)
    parser.add_argument('-sbo', '--small-buffer-optimization', nargs='?', type=bool, required=False,
                        const=True, default=False,
                        help='enables small buffer optimization')
    parser.add_argument('--interface-file', type=str, required=False, help='write output to given file')
    parser.add_argument('--header-only', action='store_true',
                        help='disables generation of source files')
    parser.add_argument('--buffer', nargs='?', type=str, required=False,
                        default='128',
                        help='buffer size or c++-macro specifying the buffer size')
    parser.add_argument('--detail-file', nargs='?', type=str, required=False,
                        default='detail.hh',
                        help='file for implementation details')
    parser.add_argument('--detail-folder', nargs='?', type=str, required=False,
                        default='handles',
                        help='folder for implementation details')
    parser.add_argument('--util-path', nargs='?', type=str, required=False,
                        default='utils',
                        help='path for storing utility files')
    parser.add_argument('--util-include-path', nargs='?', type=str, required=False,
                        default='utils',
                        help='relative include path for utility-files')
    parser.add_argument('--interface-include-path', nargs='?', type=str, required=False,
                        default='',
                        help='relative include path for the generated interface')
    parser.add_argument('--no-warning-header', nargs='?', type=str, required=False,
                        default='',
                        help='disables the generation of a warning comment that tells you not to overwrite '
                             'automatically generated files')
    parser.add_argument('--std', nargs='?', type=str, required=False,
                        default='c++14',
                        help='choose the C++-standard to support')
    #TODO should support more directories
    parser.add_argument('--include-dir', type=str, required=False,
                        default='',
                        help='specify an additional include directory for libclang')
    parser.add_argument('--include-dirs', nargs='+', type=str, required=False,
                        default=[],
                        help='specify an additional include directory for libclang')
    parser.add_argument('--no-rtti', action='store_true',
                        help='do not use rtti, i.e. use static_cast instead of dynamic_cast')
    return parser


class Data:
    def __init__(self, args):
        self.file = args.file
        self.table = args.table
        self.small_buffer_optimization = args.small_buffer_optimization
        self.copy_on_write = args.copy_on_write
        self.header_only = args.header_only
        self.non_copyable = args.non_copyable
        self.buffer = args.buffer
        self.detail_file = args.detail_file
        self.interface_file = args.interface_file
        self.detail_folder = args.detail_folder
        self.detail_extension = args.detail_extension
        self.detail_namespace = args.detail_namespace
        self.util_path = args.util_path
        self.util_include_path = args.util_include_path
        self.no_warning_header = args.no_warning_header
        self.no_rtti = args.no_rtti
        if args.interface_include_path:
            self.interface_include_path = args.interface_include_path
        else:
            self.interface_include_path = os.path.basename(self.interface_file)

        self.interface_type = 'Interface'
        self.interface_variable = 'interface'

        # pointer to implementation
        self.impl_member = 'impl_'
        self.impl_raw_member = self.impl_member
        if self.table:
            if self.copy_on_write:
                self.impl_raw_member += ' . get ( )'
        else:
            if self.copy_on_write or (not self.copy_on_write and not self.small_buffer_optimization):
                self.impl_raw_member += ' . get ( )'
        self.impl_access = 'write ( )' if self.copy_on_write else 'impl_'
        self.impl_const_access = 'read ( )' if self.copy_on_write else 'impl_'

        # libclang
        self.clang_args = [args.file]
        self.clang_args.extend(args.clang_args)
        self.clang_args.append('-std=' + args.std)
        self.clang_args.append('-I' + args.include_dir)
        for dir in args.include_dirs:
            self.clang_args.append('-I' + dir)

        # for file_parser, which is based on libclang
        self.current_namespaces = []
        self.current_struct = clang.cindex.conf.lib.clang_getNullCursor()


    def get_impl_type(self, namespace, classname):
        if self.table:
            if self.copy_on_write:
                return 'std :: shared_ptr < void > '
            else:
                return 'void * '
        else:
            if self.small_buffer_optimization and self.copy_on_write:
                return 'std :: shared_ptr < ' + namespace + ' :: HandleBase < ' + classname + ' , Buffer > >'
            if self.small_buffer_optimization and not self.copy_on_write:
                return namespace + ' :: HandleBase < ' + classname + ' , Buffer > *'
            if self.copy_on_write:
                return 'std :: shared_ptr < ' + namespace + ' :: HandleBase < ' + classname + ' > >'
            else:
                return 'std :: unique_ptr < ' + namespace + ' :: HandleBase < ' + classname + ' > >'


def get_table_data(args):
    data = Data(args)
    data.function_table_type = 'Functions'
    data.function_table_member = 'functions_'
    data.read_function = None
    data.write_function = None
    return data


def get_handle_data(args):
    data = Data(args)
    data.handle_type = 'Handle < T , Interface , Buffer , HeapAllocated >' if data.small_buffer_optimization else 'Handle < T , Interface >'
    data.handle_base_typename = 'HandleBase'
    data.handle_base_type = data.handle_base_typename + (' < Interface , Buffer >' if data.small_buffer_optimization else ' < Interface > ')
    return data


def get_data(args):
    if args.table:
        return get_table_data(args)
    else:
        return get_handle_data(args)


def copy_utility_file(args):
    if args.table:
        call(["cp", os.path.join(os.path.dirname(__file__), 'util', 'table_util.hh'), args.util_path])
    else:
        call(["cp", os.path.join(os.path.dirname(__file__), 'util', 'util.hh'), args.util_path])


def generate_type_erased_interface(args):
    type_erasure.detail_generator.write_file(get_data(args))
    type_erasure.interface_generator.write_file(get_data(args))


def format_generated_files(args):
    # format files
    abs_path = os.path.join(os.getcwd(), args.detail_folder, args.detail_file)
    type_erasure.util.clang_format(abs_path)
    abs_path = os.path.join(os.getcwd(), args.interface_file)
    type_erasure.util.clang_format(abs_path)
    if not args.header_only:
        abs_path = os.path.join(os.getcwd(), type_erasure.interface_generator.get_source_filename(args.interface_file))
        type_erasure.util.clang_format(abs_path)


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    copy_utility_file(args)
    generate_type_erased_interface(args)
    format_generated_files(args)