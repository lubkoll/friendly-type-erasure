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
    if not data.copy_on_write:
        destroy = 'virtual void destroy ( ) noexcept = 0 ;'
        scope.add(cpp_file_parser.get_function_from_text(classname, 'destroy', '', destroy))


def add_handle_base(data, scope, class_scope):
    classname = 'HandleBase'

    if data.small_buffer_optimization:
        handle_base = 'template < class Buffer > struct HandleBase'
        scope.add(cpp_file_parser.get_template_struct_from_text(classname, handle_base))
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
    scope.add(cpp_file_parser.get_template_struct_from_text(classname, handle))

    add_handle_constructors(scope)
    add_overriding_functions(data, scope, classname)

    class_scope.visit(OverridingFunctionExtractor(scope))
    scope.add( cpp_file_parser.ScopeEntry('variable', 'T value_;') )

    scope.close()

    # template specialization for std::reference_wrapper
    scope.add( cpp_file_parser.ScopeEntry('code fragment', code.get_handle_specialization(data)))


class FunctionPointerExtractor(cpp_file_parser.RecursionVisitor):
    def __init__(self,scope):
        self.scope = scope

    def visit(self,entry):
        pass

    def visit_function(self,function):
        function_pointer_alias = function.name + '_function'
        function_pointer_alias_definition = 'using ' + function_pointer_alias + ' = '

        index, offset = cpp_file_parser.find_function_name(function.name, function.tokens)
        function_pointer_alias_definition += util.concat( function.tokens[:index], ' ' )
        function_pointer_alias_definition += '( * ) ( void *'
        arguments = cpp_file_parser.get_function_arguments(function)
        for arg in arguments:
            function_pointer_alias_definition += ' , ' + arg.in_declaration()
        start_index = cpp_file_parser.get_arguments_end_index(function.name, function.tokens)
        end_index = cpp_file_parser.get_declaration_end_index(function.name, function.tokens)
        for token in function.tokens[start_index:end_index]:
            if token.spelling != 'const':
                function_pointer_alias_definition += token.spelling + ' '
        function_pointer_alias_definition += ';'

        self.scope.add(cpp_file_parser.get_alias_from_text(function_pointer_alias, function_pointer_alias_definition))
        self.scope.add(cpp_file_parser.Variable(function_pointer_alias + ' ' + function.name + ';'))


def add_table(data, scope, class_scope):
    if data.small_buffer_optimization:
        function_table = 'template < class Buffer > struct function_table'
        scope.add(cpp_file_parser.get_template_struct_from_text('function_table', function_table))
    else:
        scope.add(cpp_file_parser.Struct('function_table'))
    if data.copy_on_write:
        clone_function = 'using clone_function = void ( * ) ( void * , std :: shared_ptr < void > & ) ;'
        scope.add(cpp_file_parser.get_alias_from_text('clone_function', clone_function))
        scope.add(cpp_file_parser.Variable('clone_function clone;'))
        if data.small_buffer_optimization:
            clone_into_function = 'using clone_into_function = ' \
                                  'void ( * ) ( void * , Buffer & , std :: shared_ptr < void > & ) ;'
            scope.add(cpp_file_parser.get_alias_from_text('clone_into_function', clone_into_function))
            scope.add(cpp_file_parser.Variable('clone_into_function clone_into;'))
    else:
        delete_function = 'using delete_function = void ( * ) ( void * ) noexcept ;'
        scope.add(cpp_file_parser.get_alias_from_text('delete_function', delete_function))
        scope.add(cpp_file_parser.Variable('delete_function del;'))
        clone_function = 'using clone_function = void * ( * ) ( void * ) ;'
        scope.add(cpp_file_parser.get_alias_from_text('clone_function', clone_function))
        scope.add(cpp_file_parser.Variable('clone_function clone;'))
        if data.small_buffer_optimization:
            clone_into_function = 'using clone_into_function = void * ( * ) ( void * , Buffer & ) ;'
            scope.add(cpp_file_parser.get_alias_from_text('clone_into_function', clone_into_function))
            scope.add(cpp_file_parser.Variable('clone_into_function clone_into;'))

    class_scope.visit(FunctionPointerExtractor(scope))
    scope.close()


class FunctionPointerWrapperExtractor(cpp_file_parser.RecursionVisitor):
    def __init__(self,scope, for_reference_wrapper=False):
        self.scope = scope
        self.for_reference_wrapper = for_reference_wrapper

    def visit(self,entry):
        pass

    def visit_function(self,function):
        index, offset = cpp_file_parser.find_function_name(function.name, function.tokens)
        wrapper = 'static ' +  util.concat( function.tokens[:index+offset], ' ' )
        wrapper += 'void * impl '
        arguments = cpp_file_parser.get_function_arguments(function)
        for arg in arguments:
            wrapper += ' , ' + arg.in_declaration()
        wrapper += ' ) '
        if 'noexcept' in function.tokens:
            wrapper += 'noexcept '

        wrapper += '{ ' + function.return_str  + ' static_cast '
        const = 'const ' if cpp_file_parser.is_const(function) else ''
        if self.for_reference_wrapper:
            wrapper += '< std :: reference_wrapper < Impl > * > ( impl ) -> get ( ) . '
        else:
            wrapper += '< ' + const + ' Impl * > ( impl ) -> '
        wrapper += function.name + ' ( '
        for arg in arguments:
            wrapper += arg.in_single_function_call()
            if arg is not arguments[-1]:
                wrapper += ' ,  '
        wrapper += ' ) ; }'

        self.scope.add(cpp_file_parser.get_function_from_text('execution_wrapper', function.name, function.return_str,
                                                              wrapper))


def add_execution_wrapper(data, scope, class_scope):
    execution_wrapper = 'template < class Impl > struct execution_wrapper'
    scope.add(cpp_file_parser.get_template_struct_from_text('execution_wrapper', execution_wrapper))
    class_scope.visit(FunctionPointerWrapperExtractor(scope))
    scope.close()

    execution_wrapper = 'template < class Impl > struct execution_wrapper < std :: reference_wrapper < Impl > >'
    scope.add(cpp_file_parser.get_template_struct_from_text('execution_wrapper', execution_wrapper))
    class_scope.visit(FunctionPointerWrapperExtractor(scope, for_reference_wrapper=True))
    scope.close()


def add_details(data, scope, class_scope):
    if data.table:
        add_table(data, scope, class_scope)
        add_execution_wrapper(data, scope, class_scope)
    else:
        add_handle_base(data, scope, class_scope)
        add_handle(data, scope, class_scope)


def get_detail_file_impl(data, scope, interface_scope):
    for entry in interface_scope.content:
        if util.is_namespace(entry):
            scope.add( cpp_file_parser.Namespace(entry.name) )
            get_detail_file_impl(data,scope,entry)
            scope.close()
        elif util.is_class(entry) or util.is_struct(entry):
            scope.add(cpp_file_parser.Namespace(entry.name + data.detail_extension))
            add_details(data, scope, entry)
            scope.close()


def get_detail_file(data, interface_scope):
    main_scope = cpp_file_parser.Namespace('global')
    main_scope.add( cpp_file_parser.InclusionDirective('<functional>') )
    if data.copy_on_write:
        main_scope.add(cpp_file_parser.InclusionDirective('<memory>'))
    if not data.table:
        main_scope.add( cpp_file_parser.InclusionDirective('<type_traits>') )
        main_scope.add( cpp_file_parser.InclusionDirective('<utility>') )
        main_scope.add( cpp_file_parser.InclusionDirective('"util.hh"') )

    get_detail_file_impl(data, main_scope, interface_scope)
    return main_scope


def write_file(args):
    data = parse_args(args)
    processor = cpp_file_parser.CppFileParser()
    parser = file_parser.GenericFileParser(processor, data)
    parser.parse()

    scope = get_detail_file(data, processor.content)
    to_string.write_scope(scope, data.handle_file)
    util.clang_format(data.handle_file)


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    write_file(args)
