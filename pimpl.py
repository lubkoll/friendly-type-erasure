import argparse
from clang.cindex import Config
import type_erasure.pimpl_file_writer
import type_erasure.util


def create_parser():
    parser = argparse.ArgumentParser(description='Pimpl a C++-class')
    parser.add_argument('--impl', nargs='?', type=str, required=False,
                        default='Impl',
                        help='write output to given file')
    parser.add_argument('classname', type=str,
                        help='class to be pimpled')
    parser.add_argument('file', type=str,
                        help='file containing the class to be pimpled')
    parser.add_argument('--cpp-file', nargs='?', type=str,
                        default='',
                        help="cpp file containing implementations for the class to be pimpled")
    parser.add_argument('--interface-header-file', nargs='?', type=str,
                        default='',
                        help="new name for the pimpled file")
    parser.add_argument('--interface-source-file', nargs='?', type=str,
                        default='',
                        help="new name for the pimpled file")
    parser.add_argument('--clang-path', type=str, required=False,
                        default='/usr/lib/llvm-3.8/lib',
                        help='path to libclang library')
    parser.add_argument('clang_args', metavar='Clang-arg', type=str, nargs=argparse.REMAINDER,
                        default='-std=c++14',
                        help='additional args to pass to Clang')
    return parser

def parse_args(args):
    data = type_erasure.util.client_data()
    data.impl = args.impl
    data.classname = args.classname
    data.file = args.file
    data.cpp_file = args.cpp_file
    data.interface_header_file = args.interface_header_file
    data.interface_source_file = args.interface_source_file
    data.clang_path = args.clang_path
    data.clang_args = args.clang_args
    return data

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    data = parse_args(args)
    type_erasure.pimpl_file_writer.pimpl_class(data)
