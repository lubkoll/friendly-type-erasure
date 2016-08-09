import re
from clang.cindex import TypeKind
from util import *
from file_parser import FileProcessor
from subprocess import call


friendly_type_erasure_prefix = '// Generated by friendly type erasure.\n' \
                               '// Manual changes to this file will be overwritten by the next update.\n\n'


def find_expansion_lines_for_handle_file_writer(lines):
    retval = [0] * 3
    for i in range(len(lines)):
        line = lines[i]
        try:
            namespace_prefix_pos = line.index('{namespace_prefix}')
        except:
            namespace_prefix_pos = -1
        try:
            pure_virtual_pos = line.index('{pure_virtual_members}')
        except:
            pure_virtual_pos = -1
        try:
            virtual_pos = line.index('{virtual_members}')
        except:
            virtual_pos = -1
        if namespace_prefix_pos != -1:
            retval[0] = (i, namespace_prefix_pos)
        elif pure_virtual_pos != -1:
            retval[1] = (i, pure_virtual_pos)
        elif virtual_pos != -1:
            retval[2] = (i, virtual_pos)
    return retval


def find_expansion_lines_for_vtable_execution_wrapper_file_writer(lines):
    retval = [0] * 4
    for i in range(len(lines)):
        line = lines[i]
        try:
            member_functions_pos = line.index('{member_functions}')
        except:
            member_functions_pos = -1
        try:
            reference_wrapped_member_functions_pos = line.index('{reference_wrapped_member_functions}')
        except:
            reference_wrapped_member_functions_pos = -1
        try:
            member_function_pointers_pos = line.index('{member_function_pointers}')
        except:
            member_function_pointers_pos = -1
        try:
            member_function_signatures_pos = line.index('{member_function_signatures}')
        except:
            member_function_signatures_pos = -1
        if member_functions_pos != -1:
            retval[0] = (i, member_functions_pos)
        if reference_wrapped_member_functions_pos != -1:
            retval[1] = (i, reference_wrapped_member_functions_pos)
        if member_function_pointers_pos != -1:
            retval[2] = (i, member_function_pointers_pos)
        if member_function_signatures_pos != -1:
            retval[3] = (i, member_function_signatures_pos)
    return retval


def find_expansion_lines_for_interface_file_writer(lines):
    retval = [0]
    for i in range(len(lines)):
        line = lines[i]
        try:
            nonvirtual_pos = line.index('{nonvirtual_members}')
        except:
            nonvirtual_pos = -1

        if nonvirtual_pos != -1:
            retval[0] = (i, nonvirtual_pos)
    return retval


def find_expansion_lines_for_vtable_interface_file_writer(lines):
    retval = [0] * 2
    for i in range(len(lines)):
        line = lines[i]
        try:
            member_function_vtable_initialization_pos = line.index('{member_function_vtable_initialization}')
        except:
            member_function_vtable_initialization_pos = -1
        try:
            member_functions_pos = line.index('{member_functions}')
        except:
            member_functions_pos = -1

        if member_function_vtable_initialization_pos != -1:
            retval[0] = (i, member_function_vtable_initialization_pos)
        if member_functions_pos != -1:
            retval[1] = (i, member_functions_pos)
    return retval


class Function(object):
    def __init__(self, name, signature, argument_names, return_str, is_const, ):
        self.name = name
        self.signature = signature
        self.argument_names = argument_names
        self.return_str = return_str
        self.is_const = is_const
        self.const_qualifier = (is_const and 'const ' or '')


def function_data(data,cursor):
    function_name = cursor.spelling
    return_str = cursor.result_type.kind != TypeKind.VOID and 'return ' or ''

    tokens = get_tokens(data.tu, cursor)

    str = ''
    constness = ''

    identifier_regex = re.compile(r'[_a-zA-Z][_a-zA-Z0-9]*')

    probably_args = []
    close_paren_seen = False
    for i in range(len(tokens)):
        spelling = tokens[i].spelling
        if identifier_regex.match(spelling) and i < len(tokens) - 1 and (
                tokens[i + 1].spelling == comma or tokens[i + 1].spelling == close_paren):
            probably_args.append(spelling)
        if close_paren_seen and spelling == 'const':
            constness = 'const'
        if spelling == close_paren:
            close_paren_seen = True
        if spelling == open_brace or spelling == semicolon:
            break
        if i:
            str += ' '
        str += spelling

    args = [x for x in cursor.get_arguments()]
    args_str = ''


    for i in range(len(args)):
        arg_cursor = args[i]
        # Sometimes, libclang gets confused.  When it does, try our best to
        # figure out the parameter names anyway.
        if arg_cursor.spelling == '':
            args_str = ', '.join(probably_args)
            os.write(2,
                     '''An error has occurred in determining the name of parameter {} of function
                     {}. This usually occurs when libclang can't figure out the type of the
                     parameter (often due to a typo or missing include somewhere).  We're using
                     these possibly-wrong, heuristically-determined parameter names instead:
                     '{}'.\n'''.format(i, function_name, args_str))
            break
        if i:
            args_str += ', '
        args_str += arg_cursor.spelling

    return Function( function_name, str, args_str, return_str, constness == 'const')


def is_header_file(filename):
    return filename.endswith('.hpp') or \
        filename.endswith('.hh') or \
        filename.endswith('.h')


def is_source_file(filename):
    return filename.endswith('.cpp')


def get_source_filename(filename):
    if filename.endswith('.hpp'):
        return filename.replace('.hpp','.cpp')
    if filename.endswith('.hh'):
        return filename.replace('.hh','.cpp')
    if filename.endswith('.h'):
        return filename.replace('.h','.cpp')
    return filename


def get_header_filenames(filename):
    if not filename.endswith('.cpp'):
        return [filename]
    return [filename.replace('.cpp', '.hpp'), filename.replace('.cpp', '.hh'), filename.replace('.cpp', '.h')]



class CppFileWriter(FileProcessor):
    def __init__(self, filename, base_indent, comments=None):
        self.filename = filename
        self.base_indent = base_indent
        self.comments = comments
        self.file_content = []
        self.open_namespaces = 0
        self.open_classes = 0
        self.namespace_indent = self.open_namespaces * base_indent
        self.class_indent = self.open_classes * base_indent
        self.include_guard = None
        self.current_struct_prefix = None

    def process_open_include_guard(self, filename):
        self.include_guard = extract_include_guard(filename)
        if self.include_guard is None:
            return None
        if self.comments is not None:
            if trim(self.include_guard) == '#pragma once':
                copyright_ = get_comment('', self.comments, self.include_guard)
            else:
                copyright_ = get_comment('', self.comments, self.include_guard[0])
            if copyright_ != '':
                self.file_content.append(copyright_ + '\n')
        self.file_content.append(self.include_guard)

    def process_close_include_guard(self):
        if self.include_guard is None:
            return
        trimmed_guard = trim(self.include_guard)
        if trimmed_guard != '#pragma once' and trimmed_guard != '':
            self.file_content.append('\n\n#endif')

    def process_headers(self, headers):
        for header in headers:
            self.file_content.append(header + '\n')
        if len(headers) > 0:
            self.file_content.append('\n')

    def process_open_namespace(self, namespace_name):
        namespace_prefix = 'namespace ' + namespace_name
        comment = get_comment('', self.comments,namespace_prefix)
        self.file_content.append(comment)
        self.file_content.append(self.namespace_indent + namespace_prefix + '\n')
        self.file_content.append(self.namespace_indent + '{' + '\n')
        self.open_namespaces += 1
        self.namespace_indent += self.base_indent

    def process_close_namespace(self):
        self.open_namespaces -= 1
        self.namespace_indent = self.open_namespaces * self.base_indent
        self.file_content.append(self.namespace_indent + '}')

    def process_open_class(self, data):
        self.current_struct_prefix = data.current_struct_prefix
        self.open_classes += 1
        self.class_indent += self.base_indent

    def process_close_class(self):
        self.current_struct_prefix = None
        self.open_classes -= 1
        self.class_indent = self.open_classes * self.base_indent

    def write_to_file(self):
        file_ = open(self.filename, 'w')
        file_.write( friendly_type_erasure_prefix )
        for line in self.file_content:
            file_.write(line)
        file_.write('\n ')
        file_.close()


class FormFileWriter(CppFileWriter):
    def __init__(self, filename, base_indent, comments=None):
        self.lines = None
        self.expansion_lines = None
        super(FormFileWriter,self).__init__(filename, base_indent, comments)

    def process_close_class(self):
        for line in self.lines:
            newline = '\n'
            single_lines = rtrim(line).split('\n')
            for single_line in single_lines:
                indent = self.base_indent
                if single_line == '':
                    indent = ''
                self.file_content.append(indent + single_line + newline)

        self.lines = None
        self.expansion_lines = None

        super(FormFileWriter,self).process_close_class()


class HandleFileWriter(FormFileWriter):
    def process_open_include_guard(self, filename):
        self.include_guard = extract_include_guard(filename)
        if self.include_guard is None:
            return ''

        copyright_ = ''
        if trim(self.include_guard) != '#pragma once':
            self.include_guard = self.include_guard.replace('#ifndef ', '#ifndef HANDLE_').replace('#define ', '#define HANDLE_')
        if copyright_ != '':
            self.file_content.append(copyright)
        self.file_content.append(self.include_guard)

    def process_open_class(self, data):
        self.lines = data.handle_form_lines
        self.expansion_lines = find_expansion_lines_for_handle_file_writer(self.lines)

        self.lines = map(
            lambda line: line.format(
                struct_name=data.current_struct.spelling,
                namespace_prefix='{namespace_prefix}',
                pure_virtual_members='{pure_virtual_members}',
                virtual_members='{virtual_members}'
            ),
            self.lines
        )

        self.lines[self.expansion_lines[0][0]] = "namespace " + data.handle_namespace
        self.lines[self.expansion_lines[1][0]] = ''
        self.lines[self.expansion_lines[2][0]] = ''

        super(HandleFileWriter, self).process_open_class(data)

    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[2][0]] != '':
            self.lines[self.expansion_lines[2][0]] += '\n\n'
        function = function_data(data, cursor)
        base_indent = self.namespace_indent + self.base_indent

        self.lines[self.expansion_lines[1][0]] += base_indent + 'virtual ' + function.signature + ' = 0;\n'
        self.lines[self.expansion_lines[2][0]] += \
            base_indent + 'virtual ' + function.signature + ' override\n' + \
            base_indent + '{\n' + \
            base_indent + self.base_indent + function.return_str + 'value_.' + function.name + '( ' + function.argument_names + ' );\n' + \
            base_indent + '}'


def get_type_erased_function_pointer_type(function):
    split_arguments = function.argument_names.split(',')
    ptr_type = function.signature.replace(' ' + function.name + ' ', '(*)')
    for argument in split_arguments:
        if len(argument) > 0:
            ptr_type = ptr_type.replace(' ' + trim(argument), '')
    if function.is_const and trim(ptr_type).endswith(trim(function.const_qualifier)):
        ptr_type = trim(ptr_type[:-len(function.const_qualifier)])
    return ptr_type


def get_execution_wrapper_function_type(function):
    void_ptr = 'void*'
    if len(function.argument_names) > 0:
        void_ptr += ','
    ptr_type = function.signature.replace(' ' + function.name + ' (', '(*)( ' + function.const_qualifier + void_ptr)
    split_arguments = function.argument_names.split(',')
    for argument in split_arguments:
        if len(argument) > 0:
            ptr_type = ptr_type.replace(' ' + trim(argument), '')
    if function.is_const and ptr_type.endswith(trim(function.const_qualifier)):
        ptr_type = trim(ptr_type[:-len(trim(function.const_qualifier))])
    return ptr_type



class VTableExecutionWrapperFileWriter(FormFileWriter):
    def process_open_include_guard(self, filename):
        self.include_guard = extract_include_guard(filename)
        if self.include_guard is None:
            return ''

        copyright_ = ''
        if trim(self.include_guard) != '#pragma once':
            self.include_guard = self.include_guard.replace('#ifndef ', '#ifndef EXECUTION_WRAPPER_').replace('#define ', '#define EXECUTION_WRAPPER_')
        if copyright_ != '':
            self.file_content.append(copyright)
        self.file_content.append(self.include_guard)

    def process_open_class(self, data):
        self.lines = data.handle_form_lines
        self.expansion_lines = find_expansion_lines_for_vtable_execution_wrapper_file_writer(self.lines)

        self.lines = map(
            lambda line: line.format(
                struct_name=data.current_struct.spelling,
                namespace_prefix=data.handle_namespace,
                member_functions='{member_functions}',
                reference_wrapped_member_functions='{reference_wrapped_member_functions}',
                member_function_pointers='{member_function_pointers}',
                member_function_signatures='{member_function_signatures}'
            ),
            self.lines
        )

        self.lines[self.expansion_lines[0][0]] = ''
        self.lines[self.expansion_lines[1][0]] = ''
        self.lines[self.expansion_lines[2][0]] = ''
        self.lines[self.expansion_lines[3][0]] = ''

        super(VTableExecutionWrapperFileWriter, self).process_open_class(data)

    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[0][0]] != '':
            self.lines[self.expansion_lines[0][0]] += '\n\n'
            self.lines[self.expansion_lines[1][0]] += '\n\n'
            self.lines[self.expansion_lines[2][0]] += '\n'
            self.lines[self.expansion_lines[3][0]] += '\n'
        function = function_data(data, cursor)
        base_indent = self.namespace_indent + self.base_indent

        index = function.signature.find( function.name + ' (') + len(function.name) + 1

        start_of_function_definition = base_indent + 'static ' + function.signature[:index+2] + function.const_qualifier + 'void* impl'
        if trim(function.argument_names) != '':
            start_of_function_definition += ', '
        else:
            start_of_function_definition += ' '

        if function.is_const:
            end_of_signature = function.signature[index+2:-len(function.const_qualifier)]
        else:
            end_of_signature = function.signature[index+2:]

        start_of_function_definition += \
            end_of_signature + '\n' + \
            base_indent + '{\n' + \
            base_indent + self.base_indent + function.return_str + 'static_cast<' + function.const_qualifier


        self.lines[self.expansion_lines[0][0]] += start_of_function_definition
        self.lines[self.expansion_lines[1][0]] += start_of_function_definition

        self.lines[self.expansion_lines[0][0]] += \
            'Impl*>( impl )->' + function.name + '( '
        self.lines[self.expansion_lines[1][0]] += \
            'std::reference_wrapper<Impl>* >( impl )->get( ).' + function.name + '( '

        end_of_function_definition = ''
        if trim(function.argument_names) != '':
            end_of_function_definition += function.argument_names + ' '
        end_of_function_definition += ');\n' + base_indent + '}'

        self.lines[self.expansion_lines[0][0]] += end_of_function_definition
        self.lines[self.expansion_lines[1][0]] += end_of_function_definition


        function_pointer_signature = get_execution_wrapper_function_type(function)
        function_pointer_alias = function.name + '_function_type'
        self.lines[self.expansion_lines[2][0]] += base_indent + function_pointer_alias + ' ' + function.name + ';'
        self.lines[self.expansion_lines[3][0]] += base_indent + 'using ' + function_pointer_alias + ' = ' + function_pointer_signature + ';'


def get_handle(line):
    handle_prefixes = [' ', '(', '<', '{', '[', 'const ']
    handle_extensions = [' ', '&', '*', '<', '>']
    handle_names = ['Handle', 'HandleBase']

    for extension in handle_extensions:
        for name in handle_names:
            candidate = name + extension
            if line.startswith(candidate):
                return candidate
            for prefix in handle_prefixes:
                candidate = prefix + name + extension
                if candidate in line:
                    return candidate
    return None


class HeaderOnlyVTableInterfaceFileWriter(CppFileWriter):
    def __init__(self, filename, base_indent, handle_namespace, comments=None):
        self.handle_namespace = handle_namespace
        self.lines = None
        self.expansion_lines = None
        super(HeaderOnlyVTableInterfaceFileWriter,self).__init__(filename, base_indent, comments)

    def process_open_class(self, data):
        super(HeaderOnlyVTableInterfaceFileWriter, self).process_open_class(data)

        self.lines = data.interface_form_lines
        self.expansion_lines = find_expansion_lines_for_vtable_interface_file_writer(self.lines)

        comment = get_comment('', self.comments, self.current_struct_prefix)

        if data.small_buffer_optimization:
            self.lines = map(
                lambda line: line.format(
                    buffer_size=data.buffer,
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    namespace_prefix=data.handle_namespace,
                    member_function_vtable_initialization='{member_function_vtable_initialization}',
                    member_functions='{member_functions}',
                ),
                self.lines
            )
        else:
            self.lines = map(
                lambda line: line.format(
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    namespace_prefix=data.handle_namespace,
                    member_function_vtable_initialization='{member_function_vtable_initialization}',
                    member_functions='{member_functions}',
                ),
                self.lines
            )

        self.lines[self.expansion_lines[0][0]] = ''
        self.lines[self.expansion_lines[1][0]] = ''

    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[0][0]] != '':
            self.lines[self.expansion_lines[0][0]] += ',\n'
        if self.lines[self.expansion_lines[1][0]] != '':
            self.lines[self.expansion_lines[1][0]] += '\n\n'
        function = function_data(data, cursor)
        base_indent = self.class_indent

        self.lines[self.expansion_lines[0][0]] += base_indent + 2*self.base_indent + \
                                                  '&' + data.handle_namespace + '::execution_wrapper< typename std::decay<T>::type >::' + function.name
        if data.copy_on_write:
            if function.is_const:
                impl_args = 'read( )'
            else:
                impl_args = 'write( )'
        else:
            impl_args = 'impl_'
        if function.argument_names != '':
            impl_args += ', ' + function.argument_names

        self.lines[self.expansion_lines[1][0]] += \
            base_indent + function.signature + '\n' + base_indent + '{\n' + \
            base_indent + self.base_indent + 'assert( impl_ );\n' + \
            base_indent + self.base_indent + function.return_str + 'vtable_.' + function.name + '( ' + impl_args + ' );\n' + \
            base_indent + '}'

    def process_close_class(self):
        for line in self.lines:
            split_lines = line.split('\n')
            for split_line in split_lines:
                self.file_content.append(self.namespace_indent + split_line + '\n')

        self.lines = None
        self.expansion_lines = None

        super(HeaderOnlyVTableInterfaceFileWriter,self).process_close_class()


class VTableInterfaceHeaderFileWriter(HeaderOnlyVTableInterfaceFileWriter):
    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[0][0]] != '':
            self.lines[self.expansion_lines[0][0]] += ',\n'
        if self.lines[self.expansion_lines[1][0]] != '':
            self.lines[self.expansion_lines[1][0]] += '\n\n'
        function = function_data(data, cursor)
        base_indent = self.class_indent

        self.lines[self.expansion_lines[0][0]] += \
            base_indent + 2*self.base_indent + '&' + data.handle_namespace + \
            '::execution_wrapper< typename std::decay<T>::type >::' + function.name
        self.lines[self.expansion_lines[1][0]] += base_indent + function.signature + '\n' + base_indent + ';'


class VTableInterfaceSourceFileWriter(HeaderOnlyVTableInterfaceFileWriter):
    def process_open_include_guard(self, filename):
        pass

    def process_close_include_guard(self):
        pass

    def process_open_class(self, data):
        super(VTableInterfaceSourceFileWriter, self).process_open_class(data)

        self.lines = data.interface_cpp_form_lines
        self.expansion_lines = find_expansion_lines_for_vtable_interface_file_writer(self.lines)

        self.lines = map(
            lambda line: line.format(
                struct_name=data.current_struct.spelling,
                member_functions='{member_functions}',
            ),
            self.lines
        )

        self.lines[self.expansion_lines[1][0]] = ''

    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[1][0]] != '':
            self.lines[self.expansion_lines[1][0]] += '\n\n'
        function = function_data(data, cursor)
        base_indent = self.class_indent

        if data.copy_on_write:
            if function.is_const:
                impl_args = 'read( )'
            else:
                impl_args = 'write( )'
        else:
            impl_args = 'impl_'

        if function.argument_names != '':
            impl_args += ', ' + function.argument_names

        self.lines[self.expansion_lines[1][0]] += \
            base_indent + function.signature.replace(' ' + function.name + ' ', ' ' + data.current_struct.spelling + '::' + function.name) + '\n' + \
            base_indent + '{\n' + \
            base_indent + self.base_indent + 'assert( impl_ );\n' + \
            base_indent + self.base_indent + function.return_str + 'vtable_.' + function.name + '( ' + impl_args + ' );\n' + \
            base_indent + '}'


class HeaderOnlyInterfaceFileWriter(CppFileWriter):
    def __init__(self, filename, base_indent, handle_namespace, comments=None):
        self.handle_namespace = handle_namespace
        self.lines = None
        self.expansion_lines = None
        super(HeaderOnlyInterfaceFileWriter,self).__init__(filename, base_indent, comments)

    def process_open_class(self, data):
        super(HeaderOnlyInterfaceFileWriter, self).process_open_class(data)

        self.lines = data.interface_form_lines
        self.expansion_lines = find_expansion_lines_for_interface_file_writer(self.lines)

        comment = get_comment('', self.comments, self.current_struct_prefix)

        if data.small_buffer_optimization:
            self.lines = map(
                lambda line: line.format(
                    buffer_size=data.buffer,
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    nonvirtual_members='{nonvirtual_members}',
                ),
                self.lines
            )
        else:
            self.lines = map(
                lambda line: line.format(
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    nonvirtual_members='{nonvirtual_members}',
                ),
                self.lines
            )

        self.lines[self.expansion_lines[0][0]] = ''

    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[0][0]]:
            self.lines[self.expansion_lines[0][0]] += '\n\n'
        function = function_data(data, cursor)
        base_indent = self.class_indent

        nonvirtual_member = get_comment(base_indent, self.comments, function.signature)
        nonvirtual_member += \
            base_indent + function.signature + '\n' + \
            base_indent + '{\n' + \
            base_indent + self.base_indent + 'assert(handle_);\n' + \
            base_indent + self.base_indent + function.return_str
        if data.copy_on_write:
            nonvirtual_member += (function.is_const and 'read().' or 'write().')
        else:
            nonvirtual_member += 'handle_->'
        nonvirtual_member += function.name + '(' + function.argument_names + ' );\n' + \
                             base_indent + '}'

        self.lines[self.expansion_lines[0][0]] += nonvirtual_member

    def process_close_class(self):
        for line in self.lines:
            split_lines = line.split('\n')
            for split_line in split_lines:
                if self.handle_namespace != '':
                    handle = get_handle(split_line)
                    if handle is not None:
                        new_handle = handle.replace('Handle', self.handle_namespace + '::Handle')
                        split_line = split_line.replace(handle, new_handle)
                self.file_content.append(self.namespace_indent + split_line + '\n')

        self.lines = None
        self.expansion_lines = None

        super(HeaderOnlyInterfaceFileWriter,self).process_close_class()


class InterfaceHeaderFileWriter(HeaderOnlyInterfaceFileWriter):
    def process_open_class(self, data):
        self.current_struct_prefix = data.current_struct_prefix
        self.open_classes += 1
        self.class_indent += self.base_indent

        self.lines = data.interface_form_lines
        self.expansion_lines = find_expansion_lines_for_interface_file_writer(self.lines)

        comment = get_comment('', self.comments, self.current_struct_prefix)
        if data.small_buffer_optimization:
            self.lines = map(
                lambda line: line.format(
                    buffer_size=data.buffer,
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    nonvirtual_members='{nonvirtual_members}',
                ),
                self.lines
            )
        else:
            self.lines = map(
                lambda line: line.format(
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    nonvirtual_members='{nonvirtual_members}',
                ),
                self.lines
            )

        self.lines[self.expansion_lines[0][0]] = ''

    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[0][0]]:
            self.lines[self.expansion_lines[0][0]] += '\n\n'
        function = function_data(data, cursor)
        self.lines[self.expansion_lines[0][0]] += get_comment(self.class_indent, self.comments, function.signature)
        self.lines[self.expansion_lines[0][0]] += self.class_indent + function.signature + ';'


class InterfaceSourceFileWriter(HeaderOnlyInterfaceFileWriter):
    def process_open_include_guard(self, filename):
        pass

    def process_close_include_guard(self):
        pass

    def process_open_class(self, data):
        self.current_struct_prefix = data.current_struct_prefix
        self.open_classes += 1
        self.class_indent += self.base_indent

        self.lines = data.interface_cpp_form_lines
        self.expansion_lines = find_expansion_lines_for_interface_file_writer(self.lines)

        self.lines = map(
            lambda line: line.format(
                struct_name=data.current_struct.spelling,
                nonvirtual_members='{nonvirtual_members}'
            ),
            self.lines
        )

        self.lines[self.expansion_lines[0][0]] = ''

    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[0][0]]:
            self.lines[self.expansion_lines[0][0]] += '\n\n'
        function = function_data(data, cursor)
        nonvirtual_member = \
            function.signature.replace(' ' + function.name + ' ', ' ' + data.current_struct.spelling + '::' + function.name) + ' \n' + \
            '{\n' + \
            self.base_indent + 'assert(handle_);\n' + \
            self.base_indent + function.return_str
        if data.copy_on_write:
            nonvirtual_member += (function.is_const and 'read().' or 'write().')
        else:
            nonvirtual_member += 'handle_->'
        nonvirtual_member += function.name + '(' + function.argument_names + ' );\n' + '}'

        self.lines[self.expansion_lines[0][0]] += nonvirtual_member


class DistributedFileWriter(FileProcessor):
    def __init__(self, header_filewriter, source_filewriter):
        self.header_filewriter = header_filewriter
        self.source_filewriter = source_filewriter

    def process_open_include_guard(self, filename):
        self.header_filewriter.process_open_include_guard(filename)
        self.source_filewriter.process_open_include_guard(filename)

    def process_close_include_guard(self):
        self.header_filewriter.process_close_include_guard()
        self.source_filewriter.process_close_include_guard()

    def process_headers(self, headers):
        self.header_filewriter.process_headers(headers)
        self.source_filewriter.process_headers(['#include "' + self.header_filewriter.filename + '"'])

    def process_open_namespace(self, namespace_name):
        self.header_filewriter.process_open_namespace(namespace_name)
        self.source_filewriter.process_open_namespace(namespace_name)

    def process_close_namespace(self):
        self.header_filewriter.process_close_namespace()
        self.source_filewriter.process_close_namespace()

    def process_open_class(self, data):
        self.header_filewriter.process_open_class(data)
        self.source_filewriter.process_open_class(data)

    def process_close_class(self):
        self.header_filewriter.process_close_class()
        self.source_filewriter.process_close_class()

    def process_function(self, data, cursor):
        self.header_filewriter.process_function(data, cursor)
        self.source_filewriter.process_function(data, cursor)

    def write_to_file(self):
        self.header_filewriter.write_to_file()
        self.source_filewriter.write_to_file()


class InterfaceFileWriter(DistributedFileWriter):
    def __init__(self, header_filename, source_filename, base_indent, handle_namespace, comments=None):
        header_filewriter = InterfaceHeaderFileWriter(header_filename, base_indent, handle_namespace, comments)
        source_file_writer = InterfaceSourceFileWriter(source_filename, base_indent, handle_namespace)
        super(InterfaceFileWriter,self).__init__(header_filewriter, source_file_writer)


class VTableInterfaceFileWriter(DistributedFileWriter):
    def __init__(self, header_filename, source_filename, base_indent, handle_namespace, comments=None):
        header_filewriter = VTableInterfaceHeaderFileWriter(header_filename, base_indent, handle_namespace, comments)
        source_file_writer = VTableInterfaceSourceFileWriter(source_filename, base_indent, handle_namespace)
        super(VTableInterfaceFileWriter,self).__init__(header_filewriter, source_file_writer)
