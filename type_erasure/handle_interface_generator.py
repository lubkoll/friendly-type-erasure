#!/usr/bin/env python

import code
import cpp_file_parser
import file_parser
import parser_addition
import to_string
import util
import os


def add_aliases(data, scope, detail_namespace):
    if data.small_buffer_optimization:
        buffer = 'using Buffer = std :: array < char , ' + data.buffer + ' > ;'
        scope.add(cpp_file_parser.get_alias_from_text('Buffer', buffer))
        handle_base = 'using HandleBase = ' + detail_namespace + ' :: ' + data.handle_base_typename + ' < '
        handle_base += scope.get_open_scope().name + ' , '
        if data.small_buffer_optimization:
            handle_base += 'Buffer'
        handle_base += ' > ;'
        scope.add(cpp_file_parser.get_alias_from_text('HandleBase', handle_base))
        stack_allocated_handle = 'template < class T > using StackAllocatedHandle = ' + \
                                 detail_namespace + ' :: Handle < T , ' + scope.get_open_scope().name + \
                                 ' , Buffer , false > ;'
        scope.add(cpp_file_parser.get_alias_from_text('StackAllocatedHandle', stack_allocated_handle))
        heap_allocated_handle = 'template < class T > using HeapAllocatedHandle = ' + \
                                 detail_namespace + ' :: Handle < T , ' + scope.get_open_scope().name + \
                                ' , Buffer , true > ;'
        scope.add(cpp_file_parser.get_alias_from_text('HeapAllocatedHandle', heap_allocated_handle))
        scope.add(cpp_file_parser.Separator())


def add_constructors(data, scope, class_scope, detail_namespace):
    classname = class_scope.get_name()
    constexpr = '' if data.small_buffer_optimization else 'constexpr'
    constructor = code.get_default_default_constructor(classname,'noexcept',constexpr)
    scope.add( cpp_file_parser.get_function_from_text(classname, classname, '',
                                                      constructor,
                                                      cpp_file_parser.CONSTRUCTOR) )
    scope.add(cpp_file_parser.get_function_from_text(classname, classname, '',
                                                 code.get_handle_constructor(data, classname, detail_namespace),
                                                 cpp_file_parser.CONSTRUCTOR_TEMPLATE))
    if not data.copy_on_write:
        if not data.non_copyable:
            scope.add(cpp_file_parser.get_function_from_text(classname, classname, '',
                                                             code.get_copy_constructor(data, classname),
                                                             cpp_file_parser.CONSTRUCTOR))
        scope.add( cpp_file_parser.get_function_from_text(classname, classname, '',
                                                          code.get_move_constructor(data, classname),
                                                          cpp_file_parser.CONSTRUCTOR) )


def add_operators(data, scope, classname, detail_namespace):
    # assignment operators
    scope.add(cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                     code.get_assignment_from_value(data, classname, detail_namespace),
                                                     cpp_file_parser.FUNCTION_TEMPLATE))

    if not data.copy_on_write:
        if not data.non_copyable:
            scope.add(cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                             code.get_copy_operator(data, classname)))

        scope.add(cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                         code.get_move_operator(data, classname)))

    # operator bool
    function = cpp_file_parser.get_function_from_text(classname, 'operator bool', 'return ',
                                                      code.get_operator_bool_for_member_ptr(data.impl_member))
    comment = code.get_operator_bool_comment(function.get_declaration())
    scope.add(cpp_file_parser.Comment(comment))
    scope.add(function)


def add_casts(data, scope, classname, detail_namespace):
    function = cpp_file_parser.get_function_from_text(classname, 'target', 'return ',
                                                      code.get_cast(data, classname, detail_namespace, ''),
                                                      cpp_file_parser.FUNCTION_TEMPLATE)
    comment = code.get_handle_cast_comment(function.get_declaration())
    scope.add(cpp_file_parser.Comment(comment))
    scope.add(function)

    function = cpp_file_parser.get_function_from_text(classname, 'target', 'return ',
                                                      code.get_cast(data, classname, detail_namespace, 'const'),
                                                      cpp_file_parser.FUNCTION_TEMPLATE)
    comment = code.get_handle_cast_comment(function.get_declaration(), 'const')
    scope.add(cpp_file_parser.Comment(comment))
    scope.add(function)


def add_default_interface(data, scope, class_scope, detail_namespace):
    classname = class_scope.get_name()
    scope.add( cpp_file_parser.AccessSpecifier(cpp_file_parser.PRIVATE) )
    add_aliases(data, scope, detail_namespace)
    scope.add( cpp_file_parser.AccessSpecifier(cpp_file_parser.PUBLIC) )
    add_constructors(data, scope, class_scope, detail_namespace)
    if not data.copy_on_write and data.small_buffer_optimization:
        destructor = '~ ' + classname + ' ( ) { reset ( ) ; }'
        scope.add( cpp_file_parser.get_function_from_text(classname, '~'+classname, '',
                                                                 destructor, 'destructor'))

    add_operators(data, scope, classname, detail_namespace)


def add_private_section(data, scope, detail_namespace, classname):
    scope.add(cpp_file_parser.AccessSpecifier(cpp_file_parser.PRIVATE))

    if data.copy_on_write:
        if data.copy_on_write and data.small_buffer_optimization:
            return_type = data.handle_base_typename
        else:
            return_type = data.handle_base_typename + ' < ' + classname
            if data.small_buffer_optimization:
                return_type += ' , Buffer '
            return_type += ' > '
        return_type += ' & '
        if not data.small_buffer_optimization:
            return_type = return_type.replace(data.handle_base_typename, detail_namespace + ' :: ' + data.handle_base_typename)
        const_return_type = 'const ' + return_type

        scope.add(cpp_file_parser.get_function_from_text(classname, 'read', 'return ',
                                                         code.get_read_function(data, const_return_type,
                                                                                data.impl_member)))
        scope.add(cpp_file_parser.get_function_from_text(classname, 'write', 'return ',
                                                         code.get_write_function(data, return_type, data.impl_member)))

    if data.small_buffer_optimization and not data.copy_on_write:
        reset = 'void reset ( ) noexcept { if ( ' + data.impl_member + ' ) ' + data.impl_member + ' -> destroy ( ) ; }'
        scope.add(cpp_file_parser.get_function_from_text(classname, 'reset', '', reset))

    scope.add(cpp_file_parser.Variable(data.get_impl_type(detail_namespace, classname) + ' ' + data.impl_member + ' = nullptr;'))

    if data.small_buffer_optimization:
        scope.add(cpp_file_parser.Variable('Buffer buffer_ ;'))


class HandleFunctionExtractor(cpp_file_parser.RecursionVisitor):
    def __init__(self, data, scope):
        self.data = data
        self.scope = scope
        self.in_private_section = True

    def visit_access_specifier(self, access_specifier):
        self.in_private_section = access_specifier.value == cpp_file_parser.PRIVATE
        if not self.in_private_section:
            self.scope.add(access_specifier)

    def visit_alias(self, alias):
        if self.in_private_section:
            return
        self.scope.add(alias)

    def visit(self,entry):
        if self.in_private_section:
            return
        self.scope.add(entry)

    def visit_class(self,class_):
        self.in_private_section = class_.type == cpp_file_parser.CLASS
        super(HandleFunctionExtractor,self).visit_class(class_)

    def visit_function(self,function):
        if self.in_private_section:
            return

        code = util.concat(function.tokens[:cpp_file_parser.get_declaration_end_index(function.name, function.tokens)], ' ')
        code += ' { assert ( ' + self.data.impl_member + ' ) ; ' + function.return_str
        if self.data.copy_on_write:
            if cpp_file_parser.is_const(function):
                code += 'read ( ) . '
            else:
                code += 'write ( ) . '
        else:
            code += self.data.impl_member + ' -> '
        code += cpp_file_parser.get_function_name_for_type_erasure(function) + ' ( * this '
        arguments = cpp_file_parser.get_function_arguments(function)
        for arg in arguments:
            code += ' , '
            if self.scope.get_open_scope().name + ' &' in arg.type():
                code += ' * ' + arg.in_single_function_call() + ' . ' + self.data.impl_member + ' '
            elif self.scope.get_open_scope().name + ' *' in arg.type():
                    code += arg.in_single_function_call() + ' -> ' + self.data.impl_member
            else:
                code += arg.in_single_function_call()
        code += ' ) ; }'

        self.scope.add(cpp_file_parser.get_function_from_text(function.classname, function.name, function.return_str, code))


def get_private_base_class(classname, data):
    private_base_class = classname + data.detail_extension + ' :: ' + data.function_table_type + ' < ' + classname
    if data.small_buffer_optimization:
        private_base_class += ' , ' + classname + ' :: Buffer'
    private_base_class += ' >'
    return private_base_class


def add_interface(data, scope, class_scope, detail_namespace):
    if cpp_file_parser.is_class(class_scope):
        scope.add(cpp_file_parser.Class(class_scope.get_name(), class_scope.get_tokens()))
    else:
        scope.add(cpp_file_parser.Struct(class_scope.get_name(), class_scope.get_tokens()))

    add_default_interface(data, scope, class_scope, detail_namespace)

    class_scope.visit(HandleFunctionExtractor(data, scope))
    add_casts(data, scope, class_scope.get_name(), detail_namespace)

    add_private_section(data, scope, detail_namespace, class_scope.get_name())
    scope.close()


def get_interface_file_impl(data, scope, interface_scope):
    for entry in interface_scope.content:
        if cpp_file_parser.is_namespace(entry):
            scope.add(cpp_file_parser.Namespace(entry.name))
            get_interface_file_impl(data, scope, entry)
            scope.close()
        elif (cpp_file_parser.is_class(entry) or cpp_file_parser.is_struct(entry)) and not cpp_file_parser.is_forward_declaration(entry):
            add_interface(data, scope, entry, entry.name + data.detail_extension)
        else:
            scope.add(entry)


def get_interface_file(data, interface_scope, for_header_file=True):
    main_scope = cpp_file_parser.Namespace('global')
    relative_folder = os.path.relpath(data.detail_folder,os.path.dirname(data.interface_file))
    if for_header_file:
        main_scope.add(cpp_file_parser.InclusionDirective('"' + os.path.join(relative_folder,data.detail_file) + '"'))
        if data.small_buffer_optimization:
            main_scope.add(cpp_file_parser.InclusionDirective('<array>'))
        if not data.copy_on_write:
            main_scope.add(cpp_file_parser.InclusionDirective('<memory>'))

    get_interface_file_impl(data, main_scope, interface_scope)

    if not for_header_file:
        cpp_file_parser.remove_inclusion_directives(main_scope)
        cpp_file_parser.prepend_inclusion_directives(main_scope,
                                                     [cpp_file_parser.InclusionDirective('"' + data.interface_include_path + '"')])

    return main_scope


def get_source_filename(header_filename):
    for ending in ['.hh', '.h', '.hpp']:
        header_filename = header_filename.replace(ending,'.cpp')
    return header_filename


def write_file(data):
    processor = cpp_file_parser.CppFileParser()
    parser = file_parser.GenericFileParser(processor, data)
    parser.parse()

    scope = get_interface_file(data, processor.scope)
    scope.visit(cpp_file_parser.SortClass())
    include_guard = parser_addition.extract_include_guard(data.file)
    scope.content.insert(0, cpp_file_parser.IncludeGuard(include_guard))
    if not include_guard.startswith('#pragma once'):
        scope.content.append(cpp_file_parser.ScopeEntry('Macro endif', '#endif\n'))

    cpp_file_parser.add_comments(scope, parser_addition.extract_comments(data.file))

    if data.header_only:
        to_string.write_scope(scope, data.interface_file, to_string.Visitor(), not data.no_warning_header)
    else:
        to_string.write_scope(scope, data.interface_file, to_string.VisitorForHeaderFile(), not data.no_warning_header)
        source_filename = get_source_filename(data.interface_file)

        scope = get_interface_file(data, processor.scope, for_header_file=False)
        scope.visit(cpp_file_parser.SortClass())
        to_string.write_scope(scope, source_filename, to_string.VisitorForSourceFile(), not data.no_warning_header)

