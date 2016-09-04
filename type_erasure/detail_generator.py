#!/usr/bin/env python

import code
import to_string
import util
import file_parser
import cpp_file_parser
import parser_addition
import os


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
    clone = 'virtual ' + code.get_return_type(data, classname) + 'clone ( ) const = 0 ;'
    scope.add( cpp_file_parser.get_function_from_text(classname, 'clone', 'return ', clone) )


def add_pure_virtual_functions_for_small_buffer_optimization(data, scope, classname):
    clone_into = 'virtual ' + code.get_return_type(data, classname) + 'clone_into ( Buffer & ) const = 0 ;'
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
        clone = code.get_return_type(data, classname) + 'clone ( ) const override { ' \
                'return ' + code.get_generator(data, classname) + '( value_ ) ; }'
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
        name = util.get_name_for_variable(function.name)
        function_pointer_alias = name + '_function'
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
            if token.spelling not in ['const','noexcept']:
                function_pointer_alias_definition += token.spelling + ' '
        function_pointer_alias_definition += ';'

        self.scope.add(cpp_file_parser.get_alias_from_text(function_pointer_alias, function_pointer_alias_definition))
        self.scope.add(cpp_file_parser.Variable(function_pointer_alias + ' ' + name + ';'))


def add_table(data, scope, class_scope):
    if data.small_buffer_optimization:
        function_table = 'template < class Buffer > struct ' + code.FUNCTION_TABLE_TYPE
        scope.add(cpp_file_parser.get_template_struct_from_text(code.FUNCTION_TABLE_TYPE, function_table))
    else:
        scope.add(cpp_file_parser.Struct(code.FUNCTION_TABLE_TYPE))
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
        delete_function = 'using delete_function = void ( * ) ( void * ) ;'
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
        name = util.get_name_for_variable(function.name)
        index, offset = cpp_file_parser.find_function_name(function.name, function.tokens)
        wrapper = 'static ' +  util.concat(function.tokens[:index], ' ')
        if function.tokens[index].spelling.startswith('operator'):
            wrapper += name + ' ( '
        else:
            wrapper += util.concat(function.tokens[index:index+offset], ' ')
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

        self.scope.add(cpp_file_parser.get_function_from_text('execution_wrapper', name, function.return_str,
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
        if cpp_file_parser.is_namespace(entry):
            scope.add( cpp_file_parser.Namespace(entry.name) )
            get_detail_file_impl(data,scope,entry)
            scope.close()
        elif cpp_file_parser.is_class(entry) or cpp_file_parser.is_struct(entry):
            scope.add(cpp_file_parser.Namespace(entry.name + data.detail_extension))
            add_details(data, scope, entry)
            scope.close()


def get_detail_file(data, interface_scope):
    main_scope = cpp_file_parser.Namespace('global')
    main_scope.add(cpp_file_parser.ScopeEntry(cpp_file_parser.INCLUDE_GUARD, '#pragma once\n'))
    for entry in interface_scope.content:
        if cpp_file_parser.is_inclusion_directive(entry):
            main_scope.add(entry)
    main_scope.add( cpp_file_parser.InclusionDirective('<functional>') )
    if data.copy_on_write:
        main_scope.add(cpp_file_parser.InclusionDirective('<memory>'))
    if not data.table:
        main_scope.add( cpp_file_parser.InclusionDirective('<type_traits>') )
        main_scope.add( cpp_file_parser.InclusionDirective('<utility>') )
        util_include_dir = data.util_include_path + '/' if data.util_include_path != data.detail_folder else ''
        main_scope.add( cpp_file_parser.InclusionDirective('<' + os.path.join(util_include_dir,'util.hh') + '>') )

    comments = parser_addition.extract_comments(data.file)
    inclusion_directives_for_forward_decl = util.get_inclusion_directives_for_forward_declarations(data, comments)
    for inclusion_directive in inclusion_directives_for_forward_decl:
        main_scope.add(cpp_file_parser.InclusionDirective(inclusion_directive))

    get_detail_file_impl(data, main_scope, interface_scope)
    return main_scope


def write_file(data):
    processor = cpp_file_parser.CppFileParser()
    parser = file_parser.GenericFileParser(processor, data)
    parser.parse()
    scope = get_detail_file(data, processor.scope)
    to_string.write_scope(scope, os.path.join(data.detail_folder,data.detail_file), to_string.Visitor(), not data.no_warning_header)
