import argparse
import clang
from clang.cindex import Config
from subprocess import call
import os
import util
import type_erasure.detail_generator
import type_erasure.interface_generator


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
    parser.add_argument('--vtable', action='store_true',
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
    parser.add_argument('--handle-file', nargs='?', type=str, required=False,
                        default='handle.hh',
                        help='write output to given file')
    parser.add_argument('--handle-folder', nargs='?', type=str, required=False,
                        default='handles',
                        help='folder for handle implementations')
    return parser


class Data:
    def __init__(self,args):
        self.file = args.file
        self.table = args.table
        self.table = args.vtable
        self.small_buffer_optimization = args.small_buffer_optimization
        self.copy_on_write = args.copy_on_write
        self.header_only = args.header_only
        self.non_copyable = args.non_copyable
        self.buffer = args.buffer
        self.handle_file = args.handle_file
        self.interface_file = args.interface_file
        self.handle_folder = args.handle_folder
        self.detail_extension = args.detail_extension
        self.detail_namespace = args.detail_namespace
        self.clang_args = args.clang_args
        self.current_namespaces = []
        self.current_struct = clang.cindex.conf.lib.clang_getNullCursor()


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    if args.table or args.vtable:
        call(["cp", os.path.join(os.path.dirname(__file__), 'forms', 'vtable_util.hh'), args.handle_folder])
    else:
        call(["cp", os.path.join(os.path.dirname(__file__), 'forms', 'util.hh'), args.handle_folder])

    type_erasure.detail_generator.write_file(Data(args))
    type_erasure.interface_generator.write_file(Data(args))

    # format files
    util.clang_format(data.handle_file)
    util.clang_format(data.interface_file)
    if not data.header_only:
        util.clang_format(type_erasure.interface_generator.get_source_file(data.interface_file))
