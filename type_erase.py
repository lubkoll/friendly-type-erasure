import argparse
import clang
from clang.cindex import Config
from subprocess import call
import os
import type_erasure.handle_generator
import type_erasure.interface_generator
from type_erasure.util import add_default_arguments


def create_parser():
    parser = argparse.ArgumentParser(description='Generates handles for type-erased C++ code.')
    add_default_arguments(parser)
    type_erasure.handle_generator.add_arguments(parser)
    type_erasure.interface_generator.add_arguments(parser)
    parser.add_argument('--handle-folder', nargs='?', type=str, required=False,
                        default='handles',
                        help='folder for handle implementations')
    return parser


def get_inheritance_based_forms(args):
    base_path = os.path.join(os.path.dirname(__file__), 'forms', 'inheritance_based')
    if args.copy_on_write and args.small_buffer_optimization:
        base_path = os.path.join(base_path, 'sbo_cow')
    elif args.copy_on_write and not args.small_buffer_optimization:
        base_path = os.path.join(base_path, 'cow')
    elif not args.copy_on_write and args.small_buffer_optimization:
        base_path = os.path.join(base_path, 'sbo')
    else:
        base_path = os.path.join(base_path, 'basic')

    return os.path.join(base_path, 'form.hpp'), os.path.join(base_path, 'handle_form.hpp')


def get_vtable_based_forms(args):
    base_path = os.path.join(os.path.dirname(__file__), 'forms', 'vtable_based')
    if args.copy_on_write and args.small_buffer_optimization:
        base_path = os.path.join(base_path, 'sbo_cow')
    elif args.copy_on_write and not args.small_buffer_optimization:
        base_path = os.path.join(base_path, 'cow')
    elif not args.copy_on_write and args.small_buffer_optimization:
        base_path = os.path.join(base_path, 'sbo')
    else:
        base_path = os.path.join(base_path, 'basic')

    return os.path.join(base_path, 'form.hpp'), os.path.join(base_path, 'execution_wrapper.hpp')


def get_forms(args):
    if args.vtable:
        return get_vtable_based_forms(args)
    else:
        return get_inheritance_based_forms(args)


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    if args.vtable:
        call(["cp", os.path.join(os.path.dirname(__file__), 'forms', 'vtable_based', 'vtable_util.hh'), args.handle_folder])
    else:
        call(["cp", os.path.join(os.path.dirname(__file__), 'forms', 'inheritance_based', 'util.hh'), args.handle_folder])

    header_path = os.path.join(os.path.dirname(__file__), 'headers')
    if args.vtable:
        if args.copy_on_write:
            args.handle_headers =  os.path.join(header_path, 'vtable_cow.hpp')
        else:
            args.handle_headers = os.path.join(header_path, 'vtable.hpp')
    else:
        if args.copy_on_write and args.small_buffer_optimization:
            args.handle_headers = os.path.join(header_path, 'sbo_cow_handle.hpp')
        else:
            args.handle_headers = os.path.join(header_path, 'handle.hpp'
                                               )
    args.interface_form, args.handle_form = get_forms(args)

    type_erasure.handle_generator.write_file(args)
    type_erasure.interface_generator.write_file(args)
