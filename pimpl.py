import argparse
import clang
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
    # parser.add_argument('--cpp-file', nargs='?', type=str,
    #                     default='',
    #                     help="cpp file containing implementations for the class to be pimpled")
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
    parser.add_argument('--non-copyable', action='store_true',
                        help='disables generation of copy constructor and assignment operator')
    parser.add_argument('--non-moveable', action='store_true',
                        help='disables generation of move constructor and assignment operator')
    parser.add_argument('-sbo', '--small-buffer_optimization', action='store_true',
                        help='disables generation of copy constructor and assignment operator')
    parser.add_argument('--implicit_default_constructor', action='store_true',
                        help='assume presence of implicitly defined default constructor')
    return parser


class Data(object):
    def __init__(self, args):
        self.impl = args.impl
        self.classname = args.classname
        self.private_classname = self.classname + self.impl
        self.file = args.file
        self.cpp_file = ''#args.cpp_file
        self.interface_header_file = args.interface_header_file
        self.interface_source_file = args.interface_source_file
        self.clang_path = args.clang_path
        self.clang_args = args.clang_args
        self.non_copyable = args.non_copyable
        self.non_moveable = args.non_moveable
        self.implicit_default_constructor = args.implicit_default_constructor
        self.small_buffer_optimization = args.small_buffer_optimization
        self.current_namespaces = []
        self.current_struct = clang.cindex.conf.lib.clang_getNullCursor()


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    data = Data(args)
    type_erasure.pimpl_file_writer.pimpl_class(data)
