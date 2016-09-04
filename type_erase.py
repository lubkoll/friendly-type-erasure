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
    parser.add_argument('--non-copyable', type=str, required=False,
                        help='set to true to generate a non-copyable interface (TODO)')
    parser.add_argument('--detail-extension', nargs='?', type=str,
                        default='Handles',
                        help='ending for namespace containing the handle or function pointer table implementation (not considered if --detail-namespace is specified)')
    parser.add_argument('--clang-path', type=str, required=False,
                        default='/usr/lib/llvm-3.8/lib',
                        help='path to libclang library')
    parser.add_argument('clang_args', metavar='Clang-arg', type=str, nargs=argparse.REMAINDER,
                        default='-std=c++14',
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
        if args.interface_include_path:
            self.interface_include_path = args.interface_include_path
        else:
            self.interface_include_path = os.path.basename(self.interface_file)
        self.clang_args = args.clang_args
        self.current_namespaces = []
        self.current_struct = clang.cindex.conf.lib.clang_getNullCursor()


def copy_utility_file(args):
    if args.table:
        call(["cp", os.path.join(os.path.dirname(__file__), 'util', 'vtable_util.hh'), args.util_path])
    else:
        call(["cp", os.path.join(os.path.dirname(__file__), 'util', 'util.hh'), args.util_path])


def generate_type_erased_interface(args):
    type_erasure.detail_generator.write_file(Data(args))
    type_erasure.interface_generator.write_file(Data(args))


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