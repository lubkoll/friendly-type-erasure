#!/usr/bin/env python

import argparse
import code
import copy
import clang
import to_string
import util
import file_parser
import cpp_file_parser


def add_arguments(parser):
    parser.add_argument('--handle-file', nargs='?', type=str, required=False,
                        default='handle.hh',
                        help='write output to given file')


def create_parser():
    parser = argparse.ArgumentParser(description='Generates handles for type-erased C++ code.')
    util.add_default_arguments(parser)
    add_arguments(parser)
    return parser


def parse_additional_args(args,data):
    data.handle_form = util.prepare_form(open(args.handle_form).read())
    data.handle_form_lines = util.prepare_form(open(args.handle_form).readlines())
    data.handle_file = args.handle_file
    return data


def parse_args(args):
    data = util.client_data()
    data = util.parse_default_args(args,data)
    data = parse_additional_args(args,data)
    return data


def add_handle_base(scope, class_scope):
    classname = 'HandleBase'
    scope.add(cpp_file_parser.Struct(classname))

    destructor = 'virtual ~ ' + classname + ' ( ) = default ;'
    scope.add( cpp_file_parser.get_function_from_text(classname, '~'+classname, '', destructor, 'destructor') )
    clone = 'virtual ' + classname + ' * clone ( ) const = 0 ;'
    scope.add( cpp_file_parser.get_function_from_text(classname, 'clone', 'return ', clone) )

    for entry in class_scope.content:
        if util.is_function(entry):
            code = util.concat(entry.tokens[:cpp_file_parser.get_declaration_end_index(entry.name,entry.tokens)],' ')

            if not code.startswith('virtual '):
                code = 'virtual ' + code
            if not code.endswith('= 0'):
                code += ' = 0'
            code += ' ;'

            scope.add( cpp_file_parser.get_function_from_text(entry.classname, entry.name, entry.return_str, code) )

    scope.close()


def add_handle(scope, class_scope):
    classname = 'Handle'
    handle = 'template < class T > struct Handle : HandleBase'
    handle_tokens = [cpp_file_parser.SimpleToken(spelling) for spelling in handle.split(' ')]
    scope.add(cpp_file_parser.TemplateStruct(classname, handle_tokens))

    # add templated constructors
    # constructor for values and rvalues
    constructor = 'template < class U , ' + code.get_static_value_check('T','U') + ' > '
    constructor += 'explicit Handle ( U && value ) ' + code.noexcept_if_nothrow_constructible
    constructor += ': value_ ( std :: forward < U > ( value ) ) { }'
    scope.add( cpp_file_parser.get_function_from_text('Handle', 'Handle', '', constructor, 'constructor') )

    # constructor for references
    constructor = 'template < class U , ' + code.static_reference_check + ' > '
    constructor += 'explicit Handle ( U && value ) noexcept : value_ ( value ) { }'
    scope.add( cpp_file_parser.get_function_from_text('Handle', 'Handle', '', constructor, 'constructor') )

    clone = classname + ' * clone ( ) const override { return new ' + classname + ' ( value_ ) ; }'
    scope.add(cpp_file_parser.get_function_from_text(classname, 'clone', 'return ', clone))

    # add interface
    for entry in class_scope.content:
        if util.is_function(entry):
            function = util.concat(entry.tokens[:cpp_file_parser.get_declaration_end_index(entry.name,entry.tokens)], ' ')

            if function.startswith('virtual '):
                function = code[len('virtual '):]
            if function.endswith(' = 0'):
                function = code[:-len(' = 0')]

            function += 'override { ' + entry.return_str + 'value_ . ' + entry.name + ' ( '
            function += cpp_file_parser.get_function_arguments_in_single_call(entry) + ' ) ; }'

            scope.add( cpp_file_parser.get_function_from_text(entry.classname, entry.name, entry.return_str, function) )

    scope.add( cpp_file_parser.ScopeEntry('variable', 'T value_;') )

    scope.close()

    # template specializatio for std::reference_wrapper
    scope.add( cpp_file_parser.ScopeEntry('code fragment', code.get_handle_specialization()))


def get_basic_handle_file_impl(data, scope, interface_scope):
    for entry in interface_scope.content:
        if util.is_namespace(entry):
            scope.add( cpp_file_parser.Namespace(entry.name) )
            get_basic_handle_file_impl(data,scope,entry)
            scope.close()
        elif util.is_class(entry) or util.is_struct(entry):
            scope.add(cpp_file_parser.Namespace(entry.name + data.detail_extension))
            add_handle_base(scope,entry)
            add_handle(scope,entry)
            scope.close()


def get_basic_handle_file(data, interface_scope):
    main_scope = cpp_file_parser.Namespace('global')
    main_scope.add( cpp_file_parser.InclusionDirective('<functional>') )
    main_scope.add( cpp_file_parser.InclusionDirective('<type_traits>') )
    main_scope.add( cpp_file_parser.InclusionDirective('<utility>') )
    main_scope.add( cpp_file_parser.InclusionDirective('"util.hh"') )
    get_basic_handle_file_impl(data, main_scope, interface_scope)
    return main_scope


def write_file(args):
    data = parse_args(args)
    processor = cpp_file_parser.CppFileParser()
    parser = file_parser.GenericFileParser(processor, data)
    parser.parse()

    scope = get_basic_handle_file(data, processor.content)
    to_string.write_scope(scope, data.handle_file)
    util.clang_format(data.handle_file)


def write_file2(args, indentation):
    data = parse_args(args)

    if data.vtable:
        file_writer = VTableExecutionWrapperFileWriter(data.handle_file, indentation)
    else:
        file_writer = HandleFileWriter(data.handle_file, indentation)
    file_writer.process_open_include_guard(args.file)
    file_writer.process_headers(extract_includes(args.handle_headers))

    file_parser = GenericFileParser(file_writer,data)
    file_parser.parse()

    file_writer.process_close_include_guard()
    file_writer.write_to_file()

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    indentation = ' ' * args.indent

    write_file(args,indentation)
