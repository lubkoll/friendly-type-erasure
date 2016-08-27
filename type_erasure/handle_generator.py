#!/usr/bin/env python

import argparse
import code
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
    data.handle_file = args.handle_file
    return data


def parse_args(args):
    data = util.client_data()
    data = util.parse_default_args(args,data)
    data = parse_additional_args(args,data)
    return data


class PureVirtualFunctionExtractor(cpp_file_parser.RecursionVisitor):
    def __init__(self,scope):
        self.scope = scope

    def visit(self,entry):
        pass

    def visit_function(self,function):
        code = util.concat(function.tokens[:cpp_file_parser.get_declaration_end_index(function.name, function.tokens)], ' ')

        if not code.startswith('virtual '):
            code = 'virtual ' + code
        if not code.endswith('= 0'):
            code += ' = 0'
        code += ' ;'

        self.scope.add(cpp_file_parser.get_function_from_text(function.classname, function.name, function.return_str, code))


def add_pure_virtual_clone_function(data, scope, classname):
    clone = 'virtual ' + util.get_return_type(data, classname) + 'clone ( ) const = 0 ;'
    scope.add( cpp_file_parser.get_function_from_text(classname, 'clone', 'return ', clone) )


def add_pure_virtual_functions_for_small_buffer_optimization(data, scope, classname):
    clone_into = 'virtual ' + util.get_return_type(data, classname) + 'clone_into ( Buffer & ) const = 0 ;'
    scope.add(cpp_file_parser.get_function_from_text(classname, 'clone_into', 'return ', clone_into))
    destroy = 'virtual void destroy ( ) noexcept = 0 ;'
    scope.add(cpp_file_parser.get_function_from_text(classname, 'destroy', '', destroy))


def add_handle_base(data, scope, class_scope):
    classname = 'HandleBase'

    if data.small_buffer_optimization:
        handle_base = 'template < class Buffer > struct HandleBase'
        handle_tokens = [cpp_file_parser.SimpleToken(spelling) for spelling in handle_base.split(' ')]
        scope.add(cpp_file_parser.TemplateStruct(classname, handle_tokens))
    else:
        scope.add(cpp_file_parser.Struct(classname))

    destructor = 'virtual ~ ' + classname + ' ( ) = default ;'
    scope.add( cpp_file_parser.get_function_from_text(classname, '~'+classname, '', destructor, 'destructor') )
    if data.small_buffer_optimization:
        add_pure_virtual_functions_for_small_buffer_optimization(data, scope, classname)
    else:
        add_pure_virtual_clone_function(data, scope, classname)

    class_scope.visit(PureVirtualFunctionExtractor(scope))

    scope.close()


class OverridingFunctionExtractor(PureVirtualFunctionExtractor):
    def visit_function(self,function):
        code = util.concat(function.tokens[:cpp_file_parser.get_declaration_end_index(function.name, function.tokens)], ' ')

        if code.startswith('virtual '):
            code = code[len('virtual '):]
        if code.endswith(' = 0'):
            code = code[:-len(' = 0')]

        code += 'override { ' + function.return_str + 'value_ . ' + function.name + ' ( '
        code += cpp_file_parser.get_function_arguments_in_single_call(function) + ' ) ; }'

        self.scope.add(cpp_file_parser.get_function_from_text(function.classname, function.name, function.return_str, code))


def add_overriding_functions(data, scope, classname):
    if data.small_buffer_optimization:
        if data.copy_on_write:
            virtual_clone_into = 'std :: shared_ptr < HandleBase < Buffer > > clone_into ( Buffer & buffer ) const override '
            virtual_clone_into += '{ if ( HeapAllocated ) return std :: make_shared < ' + classname + ' > ( value_ ) ; ' \
                                  'new ( & buffer ) ' + classname + ' ( value_ ) ; ' \
                                  'return std :: shared_ptr < ' + classname + ' > ( std :: shared_ptr < ' + classname + ' > ( ) , ' \
                                                                                                                                                                                                                              'static_cast < ' + classname + ' * >( static_cast < void * > ( &buffer ) ) ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, 'clone_into', 'return ', virtual_clone_into))
        else:
            clone_into = 'HandleBase < Buffer > * clone_into ( Buffer & buffer ) const override { return ' \
                         'type_erasure_detail :: clone_into < HandleBase < Buffer > , Handle < T , Buffer , false > , ' \
                         'Handle < T , Buffer , true > > ( value_ , buffer ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, 'clone_into', 'return ', clone_into))
        destroy = 'void destroy ( ) noexcept override { if ( HeapAllocated ) delete this ; ' \
                  'else this -> ~ ' + classname + ' ( ) ; }'
        scope.add(cpp_file_parser.get_function_from_text(classname, 'destroy', '', destroy))
    else:
        clone = util.get_return_type(data, classname) + 'clone ( ) const override { ' \
                'return ' + util.get_generator(data, classname) + '( value_ ) ; }'
        scope.add(cpp_file_parser.get_function_from_text(classname, 'clone', 'return ', clone))


def add_handle_constructors(scope):
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


def add_handle(data, scope, class_scope):
    classname = 'Handle'
    handle = ''
    if data.small_buffer_optimization:
        handle += 'template < class T , class Buffer, bool HeapAllocated > struct Handle : HandleBase < Buffer >'
    else:
        handle += 'template < class T > struct Handle : HandleBase'
    handle_tokens = [cpp_file_parser.SimpleToken(spelling) for spelling in handle.split(' ')]
    scope.add(cpp_file_parser.TemplateStruct(classname, handle_tokens))

    add_handle_constructors(scope)
    add_overriding_functions(data, scope, classname)

    class_scope.visit(OverridingFunctionExtractor(scope))
    scope.add( cpp_file_parser.ScopeEntry('variable', 'T value_;') )

    scope.close()

    # template specialization for std::reference_wrapper
    scope.add( cpp_file_parser.ScopeEntry('code fragment', code.get_handle_specialization(data)))


def get_basic_handle_file_impl(data, scope, interface_scope):
    for entry in interface_scope.content:
        if util.is_namespace(entry):
            scope.add( cpp_file_parser.Namespace(entry.name) )
            get_basic_handle_file_impl(data,scope,entry)
            scope.close()
        elif util.is_class(entry) or util.is_struct(entry):
            scope.add(cpp_file_parser.Namespace(entry.name + data.detail_extension))
            add_handle_base(data, scope, entry)
            add_handle(data, scope, entry)
            scope.close()


def get_basic_handle_file(data, interface_scope):
    main_scope = cpp_file_parser.Namespace('global')
    main_scope.add( cpp_file_parser.InclusionDirective('<functional>') )
    if data.copy_on_write:
        main_scope.add( cpp_file_parser.InclusionDirective('<memory>'))
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


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    write_file(args)
