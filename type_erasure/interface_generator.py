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
        if not data.table:
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
    constexpr = '' if data.small_buffer_optimization or data.table else 'constexpr'
    if data.table:
        constructor = classname + ' ( ) noexcept : ' + data.impl_member + ' ( nullptr ) { }'
    else:
        constructor = code.get_default_default_constructor(classname,'noexcept',constexpr)
    scope.add( cpp_file_parser.get_function_from_text(classname, classname, '',
                                                      constructor,
                                                      cpp_file_parser.CONSTRUCTOR) )

    if data.table:
        table_constructor_extractor = TableConstructorExtractor(data, class_scope.get_name(), detail_namespace)
        class_scope.visit(table_constructor_extractor)
        constructor = table_constructor_extractor.constructor + table_constructor_extractor.constructor_end
        scope.add(cpp_file_parser.get_function_from_text(class_scope.get_name(), class_scope.get_name(), '',
                                                         constructor,
                                                         cpp_file_parser.CONSTRUCTOR_TEMPLATE))
    else:
        scope.add(cpp_file_parser.get_function_from_text(classname, classname, '',
                                                     code.get_handle_constructor(data, classname, detail_namespace),
                                                     cpp_file_parser.CONSTRUCTOR_TEMPLATE))
    if not data.copy_on_write or (data.table and data.copy_on_write and data.small_buffer_optimization):
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

    if not data.copy_on_write or (data.table and data.copy_on_write and data.small_buffer_optimization):
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
    if not data.copy_on_write:
        if data.table and not data.small_buffer_optimization:
            destructor = '~ ' + classname + ' ( ) { if ( ' + data.impl_member + ' ) '
            destructor += data.function_table_member + ' . del ( ' + data.impl_member + ' ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, '~'+classname, '',
                                                         destructor, 'destructor'))
        else:
            if data.small_buffer_optimization:
                destructor = '~ ' + classname + ' ( ) { reset ( ) ; }'
                scope.add( cpp_file_parser.get_function_from_text(classname, '~'+classname, '',
                                                                     destructor, 'destructor'))

    add_operators(data, scope, classname, detail_namespace)
#    add_casts(data, scope, classname, detail_namespace)


def add_private_section(data, scope, detail_namespace, classname):
    scope.add(cpp_file_parser.AccessSpecifier(cpp_file_parser.PRIVATE))

    if data.copy_on_write:
        if data.table:
            return_type = 'void *'
            const_return_type = return_type
        else:
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

    if data.table:
        function_table_var = detail_namespace + '::' + data.function_table_type + '<' + classname
        if data.small_buffer_optimization:
            function_table_var += ', Buffer'
        function_table_var += '>' + data.function_table_member + ';'
        scope.add(cpp_file_parser.Variable(function_table_var))

        if data.copy_on_write:
            scope.add(cpp_file_parser.Variable('std::shared_ptr<void> ' + data.impl_member + ' = nullptr;'))
        else:
            scope.add(cpp_file_parser.Variable('void* ' + data.impl_member + ' = nullptr;'))
        if data.small_buffer_optimization and not data.copy_on_write:
            reset = 'void reset ( ) noexcept { if ( ' + data.impl_member + ' && type_erasure_vtable_detail :: is_heap_allocated ' \
                    '( ' + data.impl_raw_member + ' , buffer_ ) ) ' + data.function_table_member + ' . del ( ' + data.impl_member + ' ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, 'reset', '', reset))

            clone_into = 'void * clone_into ( Buffer & buffer ) const { if ( ! ' + data.impl_member + ' ) return nullptr ; '
            clone_into += 'if ( type_erasure_vtable_detail :: is_heap_allocated ( ' + data.impl_raw_member + ' , buffer_ ) ) '
            clone_into += 'return ' + data.function_table_member + ' . clone ( ' + data.impl_member + ' ) ; else '
            clone_into += 'return ' + data.function_table_member + ' . clone_into ( ' + data.impl_member + ' , buffer ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, 'clone_into', 'return ', clone_into))

    else:
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
        code += util.get_function_name_for_type_erasure(function.name) + ' ( * this '
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


class TableConstructorExtractor(cpp_file_parser.RecursionVisitor):
    def __init__(self, data, classname, detail_namespace):
        constructor = code.get_constructor_from_value_declaration(classname) + ' : ' + data.function_table_member + ' ( { '
        if not data.copy_on_write:
            constructor += '& type_erasure_vtable_detail :: delete_impl < ' + code.get_decayed('T') + ' > , '
            constructor += '& type_erasure_vtable_detail :: clone_impl < ' + code.get_decayed('T') + ' >'
            if data.small_buffer_optimization:
                constructor += ' , & type_erasure_vtable_detail :: clone_into_buffer < ' + code.get_decayed('T') + ' , Buffer >'
        else:
            constructor += '& type_erasure_vtable_detail :: clone_into_shared_ptr < ' + code.get_decayed('T') + ' >'
            if data.small_buffer_optimization:
                constructor += ' , & type_erasure_vtable_detail :: clone_into_buffer < ' + code.get_decayed('T') + ' , Buffer >'
        self.constructor = constructor
        self.classname = classname

        constructor_end = ' } ) '
        if data.small_buffer_optimization:
            constructor_end += ' , ' + data.impl_member + ' ( nullptr ) { '
            constructor_end += ' if ( sizeof ( ' + code.get_decayed('T') + ' ) <= sizeof ( Buffer ) ) '
            constructor_end += '{ new ( & buffer_ ) ' + code.get_decayed('T') + ' ( std :: forward < T > ( value ) ) ; '
            if data.copy_on_write:
                constructor_end += data.impl_member + ' = std :: shared_ptr < ' + code.get_decayed('T') + ' > ( '
                constructor_end += 'std :: shared_ptr < ' + code.get_decayed('T') + ' >  ( ) , '
                constructor_end += 'static_cast < ' + code.get_decayed('T') + ' * > ( static_cast < void * > ( & buffer_ ) ) ) ; } '
                constructor_end += 'else ' + data.impl_member + ' = std :: make_shared < ' + code.get_decayed('T') + ' > '
                constructor_end += '( std :: forward < T > ( value ) ) ; '
            else:
                constructor_end += data.impl_member + ' = & buffer_ ; } '
                constructor_end += 'else ' + data.impl_member + ' =  new ' + code.get_decayed('T') + ' ( std :: forward < T > ( value ) ) ;'
            constructor_end += ' }'
        else:
            constructor_end += ' , ' + data.impl_member
            if data.copy_on_write:
                constructor_end += ' ( std :: make_shared < ' + code.get_decayed('T') + ' > '
            else:
                constructor_end += ' ( new ' + code.get_decayed('T')
            constructor_end += '( std :: forward < T > ( value ) ) ) { }'
        self.constructor_end = constructor_end
        self.detail_namespace = detail_namespace

    def visit(self,visited):
        pass

    def visit_function(self,function):
        self.constructor += ' , & ' + self.detail_namespace + ' :: execution_wrapper < ' + self.classname + ' , ' + code.get_decayed('T') + ' > '
        self.constructor += ' :: ' + util.get_function_name_for_type_erasure(function.name)


class WrapperFunctionExtractor(HandleFunctionExtractor):
    def __init__(self, data, classname, scope):
        self.data = data
        self.classname = classname
        super(WrapperFunctionExtractor,self).__init__(data, scope)

    def visit_function(self,function):
        member = self.data.impl_const_access if cpp_file_parser.is_const(function) else self.data.impl_access
        if self.in_private_section:
            return
        code = function.get_declaration()
        code += '{ assert ( ' + self.data.impl_member + ' ) ; '
        code += function.return_str + self.data.function_table_member + ' . ' + util.get_function_name_for_type_erasure(function.name)
        code += ' ( * this , ' + member + ' '
#        arguments = cpp_file_parser.get_function_arguments_in_single_call(function)
        arguments = cpp_file_parser.get_function_arguments(function)
        for arg in arguments:
            code += ' , '
            if cpp_file_parser.contains(function.classname, arg.tokens):
                code += 'other . ' + self.data.impl_raw_member
            else:
                code += arg.in_single_function_call()
        code += ' ) ; }'

        self.scope.add(cpp_file_parser.get_function_from_text(self.classname,function.name,function.return_str,
                                                              code))


def add_interface(data, scope, class_scope, detail_namespace):
    if cpp_file_parser.is_class(class_scope):
        scope.add(cpp_file_parser.Class(class_scope.get_name(), class_scope.get_tokens()))
    else:
        scope.add(cpp_file_parser.Struct(class_scope.get_name(), class_scope.get_tokens()))

    add_default_interface(data, scope, class_scope, detail_namespace)

    if data.table:
        class_scope.visit(WrapperFunctionExtractor(data, class_scope.get_name(), scope))
    else:
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
        elif cpp_file_parser.is_class(entry) or cpp_file_parser.is_struct(entry):
            add_interface(data, scope, entry, entry.name + data.detail_extension)
        else:
            scope.add(entry)


def get_interface_file(data, interface_scope, for_header_file=True):
    main_scope = cpp_file_parser.Namespace('global')
    relative_folder = os.path.relpath(data.detail_folder,os.path.dirname(data.interface_file))
    if for_header_file:
        if data.table:
            main_scope.add(cpp_file_parser.InclusionDirective('"' + os.path.join(relative_folder,data.detail_file) + '"'))
            main_scope.add(cpp_file_parser.InclusionDirective('"' + data.util_include_path + '/vtable_util.hh"'))
        else:
            main_scope.add(cpp_file_parser.InclusionDirective('"' + os.path.join(relative_folder,data.detail_file) + '"'))
        if data.small_buffer_optimization:
            main_scope.add(cpp_file_parser.InclusionDirective('<array>'))
        if not data.copy_on_write:
            main_scope.add(cpp_file_parser.InclusionDirective('<memory>'))
    else:
        main_scope.add(cpp_file_parser.InclusionDirective('"' + data.interface_include_path + '"'))
    get_interface_file_impl(data, main_scope, interface_scope)
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

