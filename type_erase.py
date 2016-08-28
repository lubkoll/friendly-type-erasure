import argparse
import clang
from clang.cindex import Config
from subprocess import call
import os
import type_erasure.detail_generator
import type_erasure.interface_generator
from type_erasure.util import add_default_arguments


def create_parser():
    parser = argparse.ArgumentParser(description='Generates handles for type-erased C++ code.')
    add_default_arguments(parser)
    type_erasure.detail_generator.add_arguments(parser)
    type_erasure.interface_generator.add_arguments(parser)
    parser.add_argument('--handle-folder', nargs='?', type=str, required=False,
                        default='handles',
                        help='folder for handle implementations')
    return parser


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    if args.table or args.vtable:
        call(["cp", os.path.join(os.path.dirname(__file__), 'forms', 'vtable_util.hh'), args.handle_folder])
    else:
        call(["cp", os.path.join(os.path.dirname(__file__), 'forms', 'util.hh'), args.handle_folder])

    type_erasure.detail_generator.write_file(args)
    type_erasure.interface_generator.write_file(args)
