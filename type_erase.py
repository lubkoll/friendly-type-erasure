import argparse
import clang
import os
import sys
import type_erasure.handle_generator
import type_erasure.interface_generator


def create_parser():
    parser = argparse.ArgumentParser(description='Generates interface for type-erased C++ code.')
    parser.add_argument('-cow', '--copy-on-write', nargs='?', type=bool, required=False,
                        const=True, default=False,
                        help='enables copy on write')
    parser.add_argument('-sbo', '--small-buffer-optimization', nargs='?', type=bool, required=False,
                        const=True, default=False,
                        help='enables small buffer optimization')
    parser.add_argument('-nc', '--non-copyable', nargs='?', type=bool, default=False, const=True, required=False,
                        help='generate interfaces for non-copyable types')
    parser.add_argument('--handle_folder', type=str, default='handles', required=False,
                        help='the folder in which the handle implementation are stored')
    parser.add_argument('--header-only', nargs='?', type=bool, default=True, const=True, required=False,
                        help='to generate no source files')
    parser.add_argument('clang_path', type=str, nargs=argparse.REMAINDER,
                        default='/usr/lib/llvm-3.8/lib',
                        help='path to libclang')
    parser.add_argument('file', type=str, help='the input file containing archetypes')
    return parser


def get_handle_filename(args):
    return (args.handle_folder + '/' + args.file.replace('.', '_handle.')).replace('//', '/')


def absolute_file_path(filename):
    return os.path.join(os.getcwd(), filename)


def absolute_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)


class Args:
    def __init__(self,args):
        self.handle_form = absolute_path('forms/handle.hpp')
        self.handle_headers = absolute_path('headers/handle.hpp')
        self.interface_file = args.file.replace('plain_','')
        self.file = absolute_file_path(args.file)
        self.clang_path = args.clang_path
        self.clang_args = '-std=c++1y'
        self.handle_file = get_handle_filename(args)
        self.header_only = args.header_only
        self.indent = '    '
        self.non_copyable = args.non_copyable
        self.impl = '_impl'

        if args.copy_on_write and args.small_buffer_optimization:
            self.interface_form = absolute_path('forms/cow_sbo.hpp')

        if args.copy_on_write and not args.small_buffer_optimization:
            self.interface_form = 'forms/cow.hpp'

        if not args.copy_on_write and args.small_buffer_optimization:
            self.interface_form = 'forms/sbo.hpp'

        if not args.copy_on_write and not args.small_buffer_optimization:
            self.interface_form = absolute_path('forms/basic.hpp')


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    #if args.clang_path:
    clang.cindex.Config.set_library_path('/usr/lib/llvm-3.8/lib')

    impl_args = Args(args)

    impl_namespace_name = type_erasure.handle_generator.write_file(impl_args, impl_args.indent)
    type_erasure.write_interface.interface_generator.write_file(impl_args, impl_args.indent)
