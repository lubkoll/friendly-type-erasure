#!/usr/bin/env python

import code
import cpp
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


def add_constructors(data, scope, class_scope, detail_namespace):
    classname = class_scope.get_name()
    constructor = classname + ' ( ) noexcept : ' + data.impl_member + ' ( nullptr ) { }'
    scope.add( cpp_file_parser.get_function_from_text(classname, classname, '',
                                                      constructor,
                                                      cpp.CONSTRUCTOR) )

    table_constructor_extractor = TableConstructorExtractor(data, class_scope.get_name(), detail_namespace)
    class_scope.visit(table_constructor_extractor)
    constructor = table_constructor_extractor.constructor + table_constructor_extractor.constructor_end
    scope.add(cpp_file_parser.get_function_from_text(class_scope.get_name(), class_scope.get_name(), '',
                                                     constructor,
                                                     cpp.CONSTRUCTOR_TEMPLATE))
    if not data.copy_on_write or data.small_buffer_optimization:
        if not data.non_copyable:
            scope.add(cpp_file_parser.get_function_from_text(classname, classname, '',
                                                             code.get_copy_constructor(data, classname),
                                                             cpp.CONSTRUCTOR))
        scope.add( cpp_file_parser.get_function_from_text(classname, classname, '',
                                                          code.get_move_constructor(data, classname),
                                                          cpp.CONSTRUCTOR) )


def add_operators(data, scope, classname, detail_namespace):
    # assignment operators
    scope.add(cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                     code.get_assignment_from_value(data, classname, detail_namespace),
                                                     cpp.FUNCTION_TEMPLATE))

    if not data.copy_on_write or data.small_buffer_optimization:
        if not data.non_copyable:
            scope.add(cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                             code.get_copy_operator(data, classname)))

        scope.add(cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                         code.get_move_operator(data, classname)))

    # operator bool
    function = cpp_file_parser.get_function_from_text(classname, 'operator bool', 'return ',
                                                      code.get_operator_bool_for_member_ptr(data.impl_member))
    comment = code.get_operator_bool_comment(function.get_declaration())
    scope.add(cpp.Comment(comment))
    scope.add(function)


def add_casts(data, scope, classname, detail_namespace):
    function = cpp_file_parser.get_function_from_text(classname, 'target', 'return ',
                                                      code.get_cast(data, classname, detail_namespace, ''),
                                                      cpp.FUNCTION_TEMPLATE)
    comment = code.get_handle_cast_comment(function.get_declaration())
    scope.add(cpp.Comment(comment))
    scope.add(function)

    function = cpp_file_parser.get_function_from_text(classname, 'target', 'return ',
                                                      code.get_cast(data, classname, detail_namespace, 'const'),
                                                      cpp.FUNCTION_TEMPLATE)
    comment = code.get_handle_cast_comment(function.get_declaration(), 'const')
    scope.add(cpp.Comment(comment))
    scope.add(function)


def add_default_interface(data, scope, class_scope, detail_namespace):
    classname = class_scope.get_name()
    scope.add( cpp.private_access )
    add_aliases(data, scope, detail_namespace)
    scope.add( cpp.public_access )
    add_constructors(data, scope, class_scope, detail_namespace)
    if not data.copy_on_write:
            destructor = '~ ' + classname + ' ( ) { reset ( ) ; }'
            scope.add( cpp_file_parser.get_function_from_text(classname, '~'+classname, '',
                                                                 destructor, 'destructor'))

    add_operators(data, scope, classname, detail_namespace)
#    add_casts(data, scope, classname, detail_namespace)


def add_private_section(data, scope, detail_namespace, classname):
    scope.add(cpp.private_access)

    if data.copy_on_write:
        return_type = 'void *'
        const_return_type = return_type
        scope.add(cpp_file_parser.get_function_from_text(classname, 'read', 'return ',
                                                         code.get_read_function(data, const_return_type,
                                                                                data.impl_member)))
        scope.add(cpp_file_parser.get_function_from_text(classname, 'write', 'return ',
                                                         code.get_write_function(data, return_type)))

    function_table_var = detail_namespace + '::' + data.function_table_type + '<' + classname
    if data.small_buffer_optimization:
        function_table_var += ', Buffer'
    function_table_var += '>' + data.function_table_member + ';'
    scope.add(cpp.Variable(function_table_var))
    if not data.no_rtti:
        scope.add(cpp.Variable('std::size_t type_id_;'))

    if data.copy_on_write:
        scope.add(cpp.Variable('std::shared_ptr<void> ' + data.impl_member + ' = nullptr;'))
    else:
        scope.add(cpp.Variable('void* ' + data.impl_member + ' = nullptr;'))

    if not data.copy_on_write:
        reset = 'void reset ( ) noexcept { if ( ' + data.impl_member + ' '
        if data.small_buffer_optimization:
            reset += ' && type_erasure_table_detail :: is_heap_allocated ( ' + data.impl_raw_member + ' , buffer_ ) '
        reset += ') ' + data.function_table_member + ' . del ( ' + data.impl_raw_member + ' ) ; }'
        scope.add(cpp_file_parser.get_function_from_text(classname, 'reset', '', reset))

        if not data.non_copyable and data.small_buffer_optimization:
            clone_into = 'void * clone_into ( Buffer & buffer ) const { if ( ! ' + data.impl_member + ' ) return nullptr ; '
            clone_into += 'if ( type_erasure_table_detail :: is_heap_allocated ( ' + data.impl_raw_member + ' , buffer_ ) ) '
            clone_into += 'return ' + data.function_table_member + ' . clone ( ' + data.impl_member + ' ) ; else '
            clone_into += 'return ' + data.function_table_member + ' . clone_into ( ' + data.impl_member + ' , buffer ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, 'clone_into', 'return ', clone_into))

    if data.small_buffer_optimization:
        scope.add(cpp.Variable('Buffer buffer_ ;'))


class HandleFunctionExtractor(cpp_file_parser.RecursionVisitor):
    def __init__(self, data, scope):
        self.data = data
        self.scope = scope
        self.in_private_section = True

    def visit_access_specifier(self, access_specifier):
        self.in_private_section = access_specifier.value == cpp.PRIVATE
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
        self.in_private_section = class_.type == cpp.CLASS
        super(HandleFunctionExtractor,self).visit_class(class_)

    def visit_function(self,function):
        if self.in_private_section:
            return

        code = util.concat(function.tokens[:cpp.get_declaration_end_index(function.name, function.tokens)], ' ')
        code += ' { assert ( ' + self.data.impl_member + ' ) ; ' + function.return_str
        if self.data.copy_on_write:
            if cpp.is_const(function):
                code += 'read ( ) . '
            else:
                code += 'write ( ) . '
        else:
            code += self.data.impl_member + ' -> '
        code += cpp_file_parser.get_function_name_for_type_erasure(function) + ' ( * this '
        arguments = cpp.get_function_arguments(function)
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
        constructor = code.get_constructor_from_value_declaration(classname, detail_namespace) + ' : ' + data.function_table_member + ' ( { '
        if data.copy_on_write:
            constructor += '& type_erasure_table_detail :: clone_into_shared_ptr < ' + code.get_decayed('T') + ' >'
            if data.small_buffer_optimization:
                constructor += ' , & type_erasure_table_detail :: clone_into_buffer < ' + code.get_decayed('T') + ' , Buffer >'
        else:
            constructor += '& type_erasure_table_detail :: delete_impl < ' + code.get_decayed('T') + ' > '
            if not data.non_copyable:
                constructor += ', & type_erasure_table_detail :: clone_impl < ' + code.get_decayed('T') + ' >'
                if data.small_buffer_optimization:
                    constructor += ' , & type_erasure_table_detail :: clone_into_buffer < ' + code.get_decayed('T') + ' , Buffer >'
        self.constructor = constructor
        self.classname = classname

        constructor_end = ' } ) '
        if not data.no_rtti:
            constructor_end += ', type_id_ ( typeid ( ' + code.get_decayed('T') + ' ) . hash_code ( ) ) '
        if data.small_buffer_optimization:
            constructor_end += ', ' + data.impl_member + ' ( nullptr ) { '
            constructor_end += 'if ( sizeof ( ' + code.get_decayed('T') + ' ) <= sizeof ( Buffer ) ) '
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
        self.constructor += ' :: ' + cpp_file_parser.get_function_name_for_type_erasure(function)


class WrapperFunctionExtractor(HandleFunctionExtractor):
    def __init__(self, data, classname, scope):
        self.data = data
        self.classname = classname
        super(WrapperFunctionExtractor,self).__init__(data, scope)

    def visit_function(self,function):
        member = self.data.impl_const_access if cpp.is_const(function) else self.data.impl_access
        if self.in_private_section:
            return
        code = function.get_declaration()
        code += '{ assert ( ' + self.data.impl_member + ' ) ; '
        code += function.return_str + self.data.function_table_member + ' . ' + cpp_file_parser.get_function_name_for_type_erasure(function)
        code += ' ( * this , ' + member + ' '
        arguments = cpp.get_function_arguments(function)
        for arg in arguments:
            code += ' , '
            if cpp_file_parser.contains(function.classname, arg.tokens):
                code += arg.name() + ' . ' + self.data.impl_raw_member
            else:
                code += arg.in_single_function_call()
        code += ' ) ; }'

        self.scope.add(cpp_file_parser.get_function_from_text(self.classname,function.name,function.return_str,
                                                              code))


def add_interface(data, scope, class_scope, detail_namespace):
    if cpp.is_class(class_scope):
        scope.add(cpp.Class(class_scope.get_name(), class_scope.get_tokens()))
    else:
        scope.add(cpp.Struct(class_scope.get_name(), class_scope.get_tokens()))

    add_default_interface(data, scope, class_scope, detail_namespace)

    class_scope.visit(WrapperFunctionExtractor(data, class_scope.get_name(), scope))
    add_casts(data, scope, class_scope.get_name(), detail_namespace)

    add_private_section(data, scope, detail_namespace, class_scope.get_name())
    scope.close()


def get_interface_file_impl(data, scope, interface_scope):
    for entry in interface_scope.content:
        if cpp.is_namespace(entry):
            scope.add(cpp.Namespace(entry.name))
            get_interface_file_impl(data, scope, entry)
            scope.close()
        elif (cpp.is_class(entry) or cpp.is_struct(entry)) and not cpp.is_forward_declaration(entry):
            add_interface(data, scope, entry, entry.name + data.detail_extension)
        else:
            scope.add(entry)


def get_interface_file(data, interface_scope, for_header_file=True):
    main_scope = cpp.Namespace('global')
    relative_folder = os.path.relpath(data.detail_folder,os.path.dirname(data.interface_file))
    if for_header_file:
        main_scope.add(cpp.InclusionDirective('"' + os.path.join(relative_folder,data.detail_file) + '"'))
        main_scope.add(cpp.InclusionDirective('"' + data.util_include_path + '/table_util.hh"'))
        if data.small_buffer_optimization:
            main_scope.add(cpp.InclusionDirective('<array>'))
        if not data.copy_on_write:
            main_scope.add(cpp.InclusionDirective('<memory>'))

    get_interface_file_impl(data, main_scope, interface_scope)

    if not for_header_file:
        cpp_file_parser.remove_inclusion_directives(main_scope)
        cpp_file_parser.prepend_inclusion_directives(main_scope,
                                                     [cpp.InclusionDirective('"' + data.interface_include_path + '"')])

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
    scope.content.insert(0, cpp.IncludeGuard(include_guard))
    if not include_guard.startswith('#pragma once'):
        scope.content.append(cpp.ScopeEntry('Macro endif', '#endif\n'))

    cpp_file_parser.add_comments(scope, parser_addition.extract_comments(data.file))

    if data.header_only:
        to_string.write_scope(scope, data.interface_file, to_string.Visitor(), not data.no_warning_header)
    else:
        to_string.write_scope(scope, data.interface_file, to_string.VisitorForHeaderFile(), not data.no_warning_header)
        source_filename = get_source_filename(data.interface_file)

        scope = get_interface_file(data, processor.scope, for_header_file=False)
        scope.visit(cpp_file_parser.SortClass())
        to_string.write_scope(scope, source_filename, to_string.VisitorForSourceFile(), not data.no_warning_header)
