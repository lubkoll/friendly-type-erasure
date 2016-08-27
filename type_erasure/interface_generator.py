#!/usr/bin/env python

import argparse
import code
import cpp_file_parser
import file_parser
import parser_addition
import to_string
import util


def add_arguments(parser):
    parser.add_argument('--interface-file', type=str, required=False, help='write output to given file')
    parser.add_argument('--headers', type=str, required=False,
                        help='file containing headers to prepend to the generated code')
    parser.add_argument('--header-only', action='store_true',
                        help='disables generation of source files')
    parser.add_argument('--buffer', nargs='?', type=str, required=False,
                        default='128',
                        help='buffer size or c++-macro specifying the buffer size')


def create_parser():
    parser = argparse.ArgumentParser(description='Generates interface for type-erased C++ code.')
    add_default_arguments(parser)
    add_arguments(parser)
    return parser


def parse_additional_args(args, data):
    data.interface_file = args.interface_file
    data.header_only = args.header_only
    data.buffer = args.buffer
    return data


def parse_args(args):
    data = util.client_data()
    data = util.parse_default_args(args, data)
    data = parse_additional_args(args, data)
    data.buffer = args.buffer
    return data


def add_default_interface(data, scope, classname, detail_namespace):
    # constructors
    if data.small_buffer_optimization:
        buffer = 'using Buffer = std :: array < char , ' + data.buffer + ' > ;'
        scope.add(cpp_file_parser.get_alias_from_text('Buffer', buffer))
        handle_base = 'using HandleBase = ' + detail_namespace + ' :: HandleBase < Buffer > ;'
        scope.add(cpp_file_parser.get_alias_from_text('HandleBase', handle_base))
        stack_allocated_handle = 'template < class T > using StackAllocatedHandle = ' + \
                                 detail_namespace + ' :: Handle < T , Buffer , false > ;'
        scope.add(cpp_file_parser.get_alias_from_text('StackAllocatedHandle', stack_allocated_handle))
        heap_allocated_handle = 'template < class T > using HeapAllocatedHandle = ' + \
                                 detail_namespace + ' :: Handle < T , Buffer , true > ;'
        scope.add(cpp_file_parser.get_alias_from_text('HeapAllocatedHandle', heap_allocated_handle))
        scope.add(cpp_file_parser.Separator())

    scope.add( cpp_file_parser.AccessSpecifier(cpp_file_parser.PUBLIC) )
    constexpr = '' if data.small_buffer_optimization else 'constexpr'
    scope.add( cpp_file_parser.get_function_from_text(classname, classname, '',
                                                      code.get_default_default_constructor(classname,'noexcept',constexpr),
                                                      'constructor') )
    scope.add(cpp_file_parser.get_function_from_text(classname, classname, '',
                                                     code.get_handle_constructor(data, classname, detail_namespace),
                                                     cpp_file_parser.CONSTRUCTOR_TEMPLATE))
    if not data.copy_on_write:
        scope.add(cpp_file_parser.get_function_from_text(classname, classname, '',
                                                         code.get_handle_copy_constructor(data, classname),
                                                         'constructor'))
        scope.add( cpp_file_parser.get_function_from_text(classname, classname, '',
                                                          code.get_handle_move_constructor(data, classname),
                                                          'constructor') )
        if data.small_buffer_optimization:
            destructor = '~ ' + classname + ' ( ) { reset ( ) ; }'
            scope.add( cpp_file_parser.get_function_from_text(classname, '~'+classname, '',
                                                             destructor, 'destructor'))
        scope.add(cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                         code.get_handle_copy_operator(data, classname)))
        scope.add(cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                         code.get_handle_move_operator(data, classname)))

    # assignment operators
    scope.add( cpp_file_parser.get_function_from_text(classname, 'operator=', 'return ',
                                                      code.get_handle_assignment(data, classname, detail_namespace),
                                                      cpp_file_parser.FUNCTION_TEMPLATE) )

    # operator bool
    function = cpp_file_parser.get_function_from_text(classname, 'operator bool', 'return ',
                                                      code.get_operator_bool_for_member_ptr('handle_') )
    comment = code.get_operator_bool_comment(function.get_declaration())
    scope.add( cpp_file_parser.Comment(comment) )
    scope.add( function )

    # casts
    function = cpp_file_parser.get_function_from_text(classname, 'target', 'return ',
                                                      code.get_handle_cast(data, 'handle_', detail_namespace),
                                                      cpp_file_parser.FUNCTION_TEMPLATE)
    comment = code.get_handle_cast_comment(function.get_declaration())
    scope.add( cpp_file_parser.Comment(comment) )
    scope.add( function )

    function = cpp_file_parser.get_function_from_text(classname, 'target', 'return ',
                                                      code.get_handle_cast(data, 'handle_', detail_namespace, 'const'),
                                                      cpp_file_parser.FUNCTION_TEMPLATE)
    comment = code.get_handle_cast_comment(function.get_declaration(), 'const')
    scope.add( cpp_file_parser.Comment(comment) )
    scope.add( function )


def add_private_section(data, scope, detail_namespace, classname):
    scope.add(cpp_file_parser.AccessSpecifier(cpp_file_parser.PRIVATE))
    if data.small_buffer_optimization:
        reset = 'void reset ( ) noexcept { if ( handle_ ) handle_ -> destroy ( ) ; }'
        scope.add(cpp_file_parser.get_function_from_text(classname, 'reset', '', reset))

    if data.copy_on_write:
        handle_base = 'HandleBase'
        if not data.small_buffer_optimization:
            handle_base = detail_namespace + ' :: ' + handle_base
        scope.add(cpp_file_parser.AccessSpecifier('private'))
        scope.add(cpp_file_parser.get_function_from_text(classname, 'read', 'return ',
                                                         code.get_handle_read_function(handle_base)))
        scope.add(cpp_file_parser.get_function_from_text(classname, 'write', 'return ',
                                                         code.get_handle_write_function(data, handle_base)))

    if data.copy_on_write and data.small_buffer_optimization:
        scope.add(cpp_file_parser.Variable('std::shared_ptr< HandleBase > handle_;'))
    elif not data.copy_on_write and data.small_buffer_optimization:
        scope.add(cpp_file_parser.Variable('HandleBase * handle_ = nullptr ;'))
    elif data.copy_on_write and not data.small_buffer_optimization:
        scope.add(cpp_file_parser.Variable('std::shared_ptr< ' + detail_namespace + '::HandleBase > handle_;'))
    else:
        scope.add(cpp_file_parser.Variable('std::unique_ptr< ' + detail_namespace + '::HandleBase > handle_;'))

    if data.small_buffer_optimization:
        scope.add(cpp_file_parser.Variable('Buffer buffer_ ;'))


class HandleFunctionExtractor(cpp_file_parser.RecursionVisitor):
    def __init__(self, scope, copy_on_write):
        self.scope = scope
        self.in_private_section = True
        self.copy_on_write = copy_on_write

    def visit_access_specifier(self, access_specifier):
        self.in_private_section = access_specifier.value == cpp_file_parser.PRIVATE
        if not self.in_private_section:
            self.scope.add(access_specifier)

    def visit(self,entry):
        if self.in_private_section:
            return
        self.scope.add(entry)

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

        self.scope.add(cpp_file_parser.get_function_from_text(function.classname, function.name, function.return_str, code))


def add_interface(data, scope, class_scope, detail_namespace):
    if util.is_class(class_scope):
        scope.add(cpp_file_parser.Class(class_scope.get_name()))
    else:
        scope.add(cpp_file_parser.Struct(class_scope.get_name()))

    add_default_interface(data, scope, class_scope.get_name(), detail_namespace)

    class_scope.visit(HandleFunctionExtractor(scope, data.copy_on_write))

    add_private_section(data, scope, detail_namespace, class_scope.get_name())
    scope.close()


def get_basic_interface_file_impl(data, scope, interface_scope):
    for entry in interface_scope.content:
        if util.is_namespace(entry):
            scope.add(cpp_file_parser.Namespace(entry.name))
            get_basic_interface_file_impl(data, scope, entry)
            scope.close()
        elif util.is_class(entry) or util.is_struct(entry):
            add_interface(data, scope, entry, entry.name + data.detail_extension)
        else:
            scope.add(entry)


def get_basic_interface_file(data, interface_scope):
    main_scope = cpp_file_parser.Namespace('global')
    main_scope.add(cpp_file_parser.InclusionDirective('"handles/handle_for_' + data.interface_file + '"'))
    if data.small_buffer_optimization:
        main_scope.add(cpp_file_parser.InclusionDirective('<array>'))
    if not data.copy_on_write:
        main_scope.add(cpp_file_parser.InclusionDirective('<memory>'))
    get_basic_interface_file_impl(data, main_scope, interface_scope)
    return main_scope


def get_source_filename(header_filename):
    for ending in ['.hh','.h','.hpp']:
        header_filename = header_filename.replace(ending,'.cpp')
    return header_filename


def write_file(args):
    data = parse_args(args)
    processor = cpp_file_parser.CppFileParser()
    parser = file_parser.GenericFileParser(processor, data)
    parser.parse()

    comments = parser_addition.extract_comments(data.file)

    scope = get_basic_interface_file(data, processor.content)
    scope.visit(cpp_file_parser.SortClass())
    if data.header_only:
        to_string.write_scope(scope, data.interface_file)
        util.clang_format(data.interface_file)
    else:
        to_string.write_scope(scope, data.interface_file, to_string.VisitorForHeaderFile(comments))
        util.clang_format(data.interface_file)
        source_filename = get_source_filename(data.interface_file)

        scope.content[0] = cpp_file_parser.InclusionDirective('"' + data.interface_file + '"')
        if not data.copy_on_write:
            scope.content.pop(1)
        to_string.write_scope(scope, source_filename, to_string.VisitorForSourceFile())
        util.clang_format(source_filename)


# main
if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    if args.clang_path:
        Config.set_library_path(args.clang_path)

    write_file(args)

