#!/usr/bin/env python

import code
import copy
import cpp
import cpp_file_parser
import util


class PureVirtualFunctionExtractor(cpp_file_parser.RecursionVisitor):
    def __init__(self, data, scope):
        self.data = data
        self.scope = scope

    def visit_function(self,function_):
        function = copy.deepcopy(function_)
        tokens = function.tokens[:cpp.get_declaration_end_index(function.name, function.tokens)]
        index, offset = cpp.find_function_name(function.name, tokens)
        cpp_file_parser.replace_in_tokens(function.classname, self.data.interface_type, tokens[:index])
        function_name = cpp_file_parser.get_function_name_for_type_erasure(function)
        code = util.concat(tokens[:index], ' ') + function_name + ' ( '
        cpp_file_parser.replace_in_tokens(function.classname, 'HandleBase', tokens[index:])
        code += cpp_file_parser.const_specifier(function) + self.data.interface_type + ' & '
        for arg in cpp.get_function_arguments(function):
            code += ' , ' + arg.in_declaration()
        code += util.concat(tokens[cpp.get_arguments_end_index(function.name, tokens):
        cpp.get_declaration_end_index(function.name, tokens)], ' ')
        if not code.startswith('virtual '):
            code = 'virtual ' + code
        if not code.endswith('= 0'):
            code += ' = 0'
        code += ' ;'
        self.scope.add(cpp_file_parser.get_function_from_text(function.classname, function_name,
                                                              function.return_str, code))


def add_pure_virtual_clone_function(data, scope, classname):
    clone = 'virtual ' + code.get_handle_return_type(data, classname) + 'clone ( ) const = 0 ;'
    scope.add( cpp_file_parser.get_function_from_text(classname, 'clone', 'return ', clone) )


def add_pure_virtual_functions_for_small_buffer_optimization(data, scope, classname):
    clone_into = 'virtual ' + code.get_handle_return_type(data, classname) + 'clone_into ( Buffer & ) const = 0 ;'
    scope.add(cpp_file_parser.get_function_from_text(classname, 'clone_into', 'return ', clone_into))
    if not data.copy_on_write:
        destroy = 'virtual void destroy ( ) noexcept = 0 ;'
        scope.add(cpp_file_parser.get_function_from_text(classname, 'destroy', '', destroy))


def add_handle_base(data, scope, class_scope):
    classname = 'HandleBase'

    handle_base = 'template < class ' + data.interface_type
    if data.small_buffer_optimization:
        handle_base += ', class Buffer '
    handle_base += '> struct HandleBase'
    scope.add(cpp.get_template_struct_from_text(classname, handle_base))

    destructor = 'virtual ~ ' + classname + ' ( ) = default ;'
    scope.add( cpp_file_parser.get_function_from_text(classname, '~' + classname, '', destructor, 'destructor') )
    if data.small_buffer_optimization:
        add_pure_virtual_functions_for_small_buffer_optimization(data, scope, classname)
    else:
        add_pure_virtual_clone_function(data, scope, classname)

    class_scope.visit(PureVirtualFunctionExtractor(data, scope))

    scope.close()


class OverridingFunctionExtractor(PureVirtualFunctionExtractor):
    def visit_function(self,function_):
        function = copy.deepcopy(function_)
        tokens = function.tokens[:cpp.get_declaration_end_index(function.name, function.tokens)]
        index, offset = cpp.find_function_name(function.name, function.tokens)
        cpp_file_parser.replace_in_tokens(function.classname, self.data.interface_type, tokens[:index])
        function_name = cpp_file_parser.get_function_name_for_type_erasure(function)
        code = util.concat(tokens[:index], ' ') + function_name + ' ( '
        cpp_file_parser.replace_in_tokens(function.classname, 'HandleBase', tokens[index:])
        code += cpp_file_parser.const_specifier(function) + self.data.interface_type + ' & ' + self.data.interface_variable + ' '
        for arg in cpp.get_function_arguments(function):
            if 'HandleBase' in arg.type():
                cpp_file_parser.replace_in_tokens('HandleBase', self.data.handle_base_type, arg.tokens)
            code += ' , ' + arg.in_declaration()
        code += util.concat(tokens[cpp.get_arguments_end_index(function.name, tokens):
        cpp.get_declaration_end_index(function.name, tokens)], ' ')

        if code.startswith('virtual '):
            code = code[len('virtual '):]
        if code.endswith(' = 0'):
            code = code[:-len(' = 0')]

        code += 'override { '
        contains_class_ref = util.concat(tokens[:index], ' ') in ['const ' + self.data.interface_type + ' & ',
                                                                  self.data.interface_type + ' & ']
        if not contains_class_ref:
            code += function.return_str
        code += 'value_ . ' + function.name + ' ( '

        arguments = cpp.get_function_arguments(function)
        for arg in arguments:
            if arg.type() == 'const HandleBase & ':
                code += 'static_cast < ' + 'const ' + self.data.handle_type + ' & > ( '
                code += arg.name() + ' ) . value_ '
            elif arg.type() == 'HandleBase & ':
                code += 'static_cast < ' + self.data.handle_type + ' & > ( '
                code += arg.name() + ' ) . value_ '
            else:
                code += arg.in_single_function_call()
            if arg is not arguments[-1]:
                code += ' , '

        code += ' ) ; '
        if contains_class_ref:
            code += 'return ' + self.data.interface_variable + ' ;'
        code += ' }'

        self.scope.add(cpp_file_parser.get_function_from_text(function.classname, function_name,
                                                  function.return_str, code))


def add_overriding_functions(data, scope, classname):
    if data.small_buffer_optimization:
        if data.copy_on_write:
            virtual_clone_into = 'std :: shared_ptr < HandleBase < ' + data.interface_type + ' , Buffer > > clone_into ( Buffer & buffer ) const override '
            virtual_clone_into += '{ if ( HeapAllocated ) return std :: make_shared < ' + classname + ' > ( value_ ) ; ' \
                                  'new ( & buffer ) ' + classname + ' ( value_ ) ; ' \
                                  'return std :: shared_ptr < ' + classname + ' > ( std :: shared_ptr < ' + classname + ' > ( ) , ' \
                                                                                                                                                                                                                              'static_cast < ' + classname + ' * >( static_cast < void * > ( &buffer ) ) ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, 'clone_into', 'return ', virtual_clone_into))
        else:
            clone_into = 'HandleBase < ' + data.interface_type + ' , Buffer > * clone_into ( Buffer & buffer ) const override { return ' \
                         'type_erasure_detail :: clone_into < HandleBase < ' + data.interface_type + ' , ' \
                         ' Buffer > , Handle < T , ' + data.interface_type + ' ,  Buffer , false > , ' \
                         'Handle < T , ' + data.interface_type + ' , Buffer , true > > ( value_ , buffer ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, 'clone_into', 'return ', clone_into))
            destroy = 'void destroy ( ) noexcept override { if ( HeapAllocated ) delete this ; ' \
                      'else this -> ~ ' + classname + ' ( ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, 'destroy', '', destroy))
    else:
        clone = code.get_handle_return_type(data, classname) + 'clone ( ) const override { ' \
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
    handle = 'template < class T, class Interface '
    if data.small_buffer_optimization:
        handle += ', class Buffer, bool HeapAllocated > struct Handle : HandleBase < Interface , Buffer >'
    else:
        handle += ' > struct Handle : HandleBase < Interface >'
    scope.add(cpp.get_template_struct_from_text(classname, handle))

    add_handle_constructors(scope)
    add_overriding_functions(data, scope, classname)

    class_scope.visit(OverridingFunctionExtractor(data, scope))
    scope.add( cpp.ScopeEntry('variable', 'T value_;') )

    scope.close()

    # template specialization for std::reference_wrapper
    scope.add( cpp.ScopeEntry('code fragment', code.get_handle_specialization(data)))
