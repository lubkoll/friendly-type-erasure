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
            handle_base = 'using HandleBase = ' + detail_namespace + ' :: HandleBase < Buffer > ;'
            scope.add(cpp_file_parser.get_alias_from_text('HandleBase', handle_base))
            stack_allocated_handle = 'template < class T > using StackAllocatedHandle = ' + \
                                     detail_namespace + ' :: Handle < T , Buffer , false > ;'
            scope.add(cpp_file_parser.get_alias_from_text('StackAllocatedHandle', stack_allocated_handle))
            heap_allocated_handle = 'template < class T > using HeapAllocatedHandle = ' + \
                                     detail_namespace + ' :: Handle < T , Buffer , true > ;'
            scope.add(cpp_file_parser.get_alias_from_text('HeapAllocatedHandle', heap_allocated_handle))
            scope.add(cpp_file_parser.Separator())


def add_constructors(data, scope, class_scope, detail_namespace, impl=code.IMPL):
    classname = class_scope.get_name()
    constexpr = '' if data.small_buffer_optimization or data.table else 'constexpr'
    if data.table:
        constructor = classname + ' ( ) noexcept : ' + impl + ' ( nullptr ) { }'
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
        impl = code.IMPL if data.table else code.HANDLE
        scope.add(cpp_file_parser.get_function_from_text(classname, classname, '',
                                                         code.get_copy_constructor(data, classname, impl),
                                                         cpp_file_parser.CONSTRUCTOR))
        scope.add( cpp_file_parser.get_function_from_text(classname, classname, '',
                                                          code.get_move_constructor(data, classname, impl),
                                                          cpp_file_parser.CONSTRUCTOR) )


def add_operators(data, scope, classname, detail_namespace):
    impl = code.IMPL if data.table else code.HANDLE

    # assignment operators
    scope.add(cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                     code.get_assignment_from_value(data, classname, detail_namespace),
                                                     cpp_file_parser.FUNCTION_TEMPLATE))

    if not data.copy_on_write or (data.table and data.copy_on_write and data.small_buffer_optimization):
        scope.add(cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                         code.get_copy_operator(data, classname, impl)))

        scope.add(cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                         code.get_move_operator(data, classname, impl)))

    # operator bool
    function = cpp_file_parser.get_function_from_text(classname, 'operator bool', 'return ',
                                                      code.get_operator_bool_for_member_ptr(impl))
    comment = code.get_operator_bool_comment(function.get_declaration())
    scope.add(cpp_file_parser.Comment(comment))
    scope.add(function)


def add_casts(data, scope, classname, detail_namespace):
    impl = code.IMPL if data.table else code.HANDLE
    function = cpp_file_parser.get_function_from_text(classname, 'target', 'return ',
                                                      code.get_cast(data, impl, detail_namespace, ''),
                                                      cpp_file_parser.FUNCTION_TEMPLATE)
    comment = code.get_handle_cast_comment(function.get_declaration())
    scope.add(cpp_file_parser.Comment(comment))
    scope.add(function)

    function = cpp_file_parser.get_function_from_text(classname, 'target', 'return ',
                                                      code.get_cast(data, impl, detail_namespace, 'const'),
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
    impl = code.IMPL if data.table else code.HANDLE
    function_table = code.FUNCTION_TABLE
    if not data.copy_on_write:
        if data.table and not data.small_buffer_optimization:
            destructor = '~ ' + classname + ' ( ) { if ( ' + impl + ' ) '
            destructor += function_table + ' . del ( ' + impl + ' ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, '~'+classname, '',
                                                         destructor, 'destructor'))
        else:
            if data.small_buffer_optimization:
                destructor = '~ ' + classname + ' ( ) { reset ( ) ; }'
                scope.add( cpp_file_parser.get_function_from_text(classname, '~'+classname, '',
                                                                     destructor, 'destructor'))

    add_operators(data, scope, classname, detail_namespace)
    add_casts(data, scope, classname, detail_namespace)


def add_private_section(data, scope, detail_namespace, classname, impl, function_table=code.FUNCTION_TABLE):
    scope.add(cpp_file_parser.AccessSpecifier(cpp_file_parser.PRIVATE))

    if data.copy_on_write:
        return_type = 'void *' if data.table else 'const HandleBase &'
        if not data.small_buffer_optimization:
            return_type = return_type.replace('HandleBase', detail_namespace + ' :: HandleBase')

        scope.add(cpp_file_parser.get_function_from_text(classname, 'read', 'return ',
                                                         code.get_read_function(data, return_type, impl)))
        return_type = 'void *' if data.table else 'HandleBase &'
        if not data.small_buffer_optimization:
            return_type = return_type.replace('HandleBase', detail_namespace + ' :: HandleBase')
        scope.add(cpp_file_parser.get_function_from_text(classname, 'write', 'return ',
                                                         code.get_write_function(data, return_type, impl)))

    if data.table:
        if data.small_buffer_optimization:
            scope.add(cpp_file_parser.Variable(detail_namespace + '::function_table<Buffer>' + function_table + ';'))
        else:
            scope.add(cpp_file_parser.Variable(detail_namespace + '::function_table ' + function_table + ';'))
        if data.copy_on_write:
            scope.add(cpp_file_parser.Variable('std::shared_ptr<void> ' + impl + ' = nullptr;'))
        else:
            scope.add(cpp_file_parser.Variable('void* ' + impl + ' = nullptr;'))
        if data.small_buffer_optimization and not data.copy_on_write:
            reset = 'void reset ( ) noexcept { if ( ' + impl + ' && type_erasure_vtable_detail :: is_heap_allocated ' \
                    '( ' + impl + ' , buffer_ ) ) ' + function_table + ' . del ( ' + impl + ' ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, 'reset', '', reset))

            clone_into = 'void * clone_into ( Buffer & buffer ) const { if ( ! ' + impl + ' ) return nullptr ; '
            clone_into += 'if ( type_erasure_vtable_detail :: is_heap_allocated ( ' + impl + ' , buffer_ ) ) '
            clone_into += 'return ' + function_table + ' . clone ( impl ) ; else '
            clone_into += 'return ' + function_table + ' . clone_into ( ' + impl + ' , buffer ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, 'clone_into', 'return ', clone_into))

    else:
        if data.small_buffer_optimization and not data.copy_on_write:
            reset = 'void reset ( ) noexcept { if ( ' + impl + ' ) ' + impl + ' -> destroy ( ) ; }'
            scope.add(cpp_file_parser.get_function_from_text(classname, 'reset', '', reset))

        if data.copy_on_write and data.small_buffer_optimization:
            scope.add(cpp_file_parser.Variable('std::shared_ptr< HandleBase > handle_ = nullptr;'))
        elif not data.copy_on_write and data.small_buffer_optimization:
            scope.add(cpp_file_parser.Variable('HandleBase * handle_ = nullptr ;'))
        elif data.copy_on_write and not data.small_buffer_optimization:
            scope.add(cpp_file_parser.Variable('std::shared_ptr< ' + detail_namespace + '::HandleBase > handle_ = nullptr;'))
        else:
            scope.add(cpp_file_parser.Variable('std::unique_ptr< ' + detail_namespace + '::HandleBase > handle_ = nullptr;'))

    if data.small_buffer_optimization:
        scope.add(cpp_file_parser.Variable('Buffer buffer_ ;'))


class HandleFunctionExtractor(cpp_file_parser.RecursionVisitor):
    def __init__(self, scope, copy_on_write, comments=None):
        self.scope = scope
        self.in_private_section = True
        self.copy_on_write = copy_on_write
        self.comments = comments

    def add_comment(self,name):
        comment = util.get_comment(self.comments, name)
        if comment:
            self.scope.add(cpp_file_parser.Comment(comment))

    def visit_access_specifier(self, access_specifier):
        self.in_private_section = access_specifier.value == cpp_file_parser.PRIVATE
        if not self.in_private_section:
            self.scope.add(access_specifier)

    def visit_alias(self, alias):
        if self.in_private_section:
            return
        self.add_comment(util.concat(alias.tokens, ' '))
        self.scope.add(alias)

    def visit(self,entry):
        if self.in_private_section:
            return
        self.scope.add(entry)

    def visit_class(self,class_):
        self.in_private_section = class_.type == cpp_file_parser.CLASS
        self.add_comment(class_.type + ' ' + class_.name)
        super(HandleFunctionExtractor,self).visit_class(class_)

    def visit_function(self,function):
        if self.in_private_section:
            return

        code = util.concat(function.tokens[:cpp_file_parser.get_declaration_end_index(function.name, function.tokens)],
                           ' ')
        code += ' { assert ( handle_ ) ; ' + function.return_str
        if self.copy_on_write:
            if cpp_file_parser.is_const(function):
                code += 'read ( ) . '
            else:
                code += 'write ( ) . '
        else:
            code += 'handle_ -> '
        code += function.name + ' ( ' + cpp_file_parser.get_function_arguments_in_single_call(function) + ' ) ; }'

        self.add_comment(function.get_declaration())
        self.scope.add(cpp_file_parser.get_function_from_text(function.classname, function.name, function.return_str, code))


class TableConstructorExtractor(cpp_file_parser.RecursionVisitor):
    def __init__(self, data, classname, detail_namespace):
        constructor = code.get_constructor_from_value_declaration(classname) + ' : function_table ( { '
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

        constructor_end = ' } ) '
        if data.small_buffer_optimization:
            constructor_end += ' , impl ( nullptr ) { '
            constructor_end += ' if ( sizeof ( ' + code.get_decayed('T') + ' ) <= sizeof ( Buffer ) ) '
            constructor_end += '{ new ( & buffer_ ) ' + code.get_decayed('T') + ' ( std :: forward < T > ( value ) ) ; '
            if data.copy_on_write:
                constructor_end += 'impl = std :: shared_ptr < ' + code.get_decayed('T') + ' > ( '
                constructor_end += 'std :: shared_ptr < ' + code.get_decayed('T') + ' >  ( nullptr ) , '
                constructor_end += 'static_cast < ' + code.get_decayed('T') + ' * > ( static_cast < void * > ( & buffer_ ) ) ) ; } '
                constructor_end += 'else impl = std :: make_shared < ' + code.get_decayed('T') + ' > '
                constructor_end += '( std :: forward < T > ( value ) ) ; '
            else:
                constructor_end += 'impl = & buffer_ ; } '
                constructor_end += 'else impl =  new ' + code.get_decayed('T') + ' ( std :: forward < T > ( value ) ) ;'
            constructor_end += ' }'
        else:
            constructor_end += ' , ' + code.IMPL
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
        self.constructor += ' , & ' + self.detail_namespace + ' :: execution_wrapper < ' + code.get_decayed('T') + ' > '
        self.constructor += ' :: ' + function.name


class WrapperFunctionExtractor(HandleFunctionExtractor):
    def __init__(self, classname, scope, comments=None, member=code.IMPL, const_member=code.IMPL, function_table=code.FUNCTION_TABLE):
        self.classname = classname
        self.member = member
        self.const_member = const_member
        self.function_table = function_table
        super(WrapperFunctionExtractor,self).__init__(scope, False, comments)

    def visit_function(self,function):
        member = self.const_member if cpp_file_parser.is_const(function) else self.member
        if self.in_private_section:
            return
        code = function.get_declaration()
        code += '{ assert ( ' + self.const_member + ' ) ; '
        code += function.return_str + self.function_table + ' . ' + function.name
        code += ' ( ' + member
        arguments = cpp_file_parser.get_function_arguments_in_single_call(function)
        if arguments:
            code += ' , ' + arguments
        code += ' ) ; }'

        comment = util.get_comment(self.comments, function.get_declaration())
        if comment:
            self.scope.add(cpp_file_parser.Comment(comment))
        self.scope.add(cpp_file_parser.get_function_from_text(self.classname,function.name,function.return_str,
                                                              code))



def add_interface(data, scope, class_scope, detail_namespace):
    impl = code.IMPL if data.table else code.HANDLE
    comments = parser_addition.extract_comments(data.file)
    for comment in comments:
        print comment
    comment = util.get_comment(comments, class_scope.get_type() + ' ' + class_scope.get_name())
    if comment:
        scope.add(cpp_file_parser.Comment(comment))
    if cpp_file_parser.is_class(class_scope):
        scope.add(cpp_file_parser.Class(class_scope.get_name()))
    else:
        scope.add(cpp_file_parser.Struct(class_scope.get_name()))

    add_default_interface(data, scope, class_scope, detail_namespace)
    if data.table:
        member = impl
        const_member = impl
        if data.table and data.copy_on_write:
            member = 'write ( )'
            const_member = 'read ( )'
        class_scope.visit(WrapperFunctionExtractor(class_scope.get_name(), scope, comments, member, const_member))
    else:
        class_scope.visit(HandleFunctionExtractor(scope, data.copy_on_write, comments))

    add_private_section(data, scope, detail_namespace, class_scope.get_name(), impl)
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


def get_interface_file(data, interface_scope):
    main_scope = cpp_file_parser.Namespace('global')
    relative_folder = os.path.relpath(data.detail_folder,os.path.dirname(data.interface_file))
    if data.table:
        main_scope.add(cpp_file_parser.InclusionDirective('"' + os.path.join(relative_folder,data.detail_file) + '"'))
        main_scope.add(cpp_file_parser.InclusionDirective('"' + data.util_include_path + '/vtable_util.hh"'))
    else:
        main_scope.add(cpp_file_parser.InclusionDirective('"' + os.path.join(relative_folder,data.detail_file) + '"'))
    if data.small_buffer_optimization:
        main_scope.add(cpp_file_parser.InclusionDirective('<array>'))
    if not data.copy_on_write:
        main_scope.add(cpp_file_parser.InclusionDirective('<memory>'))
    get_interface_file_impl(data, main_scope, interface_scope)
    return main_scope


def get_source_filename(header_filename):
    for ending in ['.hh','.h','.hpp']:
        header_filename = header_filename.replace(ending,'.cpp')
    return header_filename


def write_file(data):
    processor = cpp_file_parser.CppFileParser()
    parser = file_parser.GenericFileParser(processor, data)
    parser.parse()

    scope = get_interface_file(data, processor.content)
    scope.visit(cpp_file_parser.SortClass())
    if data.header_only:
        to_string.write_scope(scope, data.interface_file)
    else:
        to_string.write_scope(scope, data.interface_file, to_string.VisitorForHeaderFile())
        source_filename = get_source_filename(data.interface_file)

        scope.content[0] = cpp_file_parser.InclusionDirective('"' + data.interface_include_path + '"')
        if not data.copy_on_write:
            scope.content.pop(1)
        to_string.write_scope(scope, source_filename, to_string.VisitorForSourceFile())
