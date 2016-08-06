import re
from clang.cindex import TypeKind
from util import *
from file_parser import FileProcessor
from subprocess import call

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


def function_data(data,cursor):
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
        if close_paren_seen and spelling == const_token:
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

    function_name = cursor.spelling

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

    return_str = cursor.result_type.kind != TypeKind.VOID and 'return ' or ''

    return [str, args_str, return_str, function_name, constness]


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
        file_.write('// Generated by friendly type erasure.\n'
                    '// Manual changes to this file will be overwritten by the next update.\n\n')
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

        self.lines[self.expansion_lines[1][0]] += base_indent + 'virtual ' + function[0] + ' = 0;\n'
        self.lines[self.expansion_lines[2][0]] += \
            base_indent + 'virtual ' + function[0] + ' override\n' + \
            base_indent + '{\n' + \
            base_indent + self.base_indent + function[2] + 'value_.' + function[3] + '( ' + function[1] + ' );\n' + \
            base_indent + '}'


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

        nonvirtual_member = get_comment(base_indent, self.comments, function[0])
        nonvirtual_member += \
            base_indent + function[0] + '\n' + \
            base_indent + '{\n' + \
            base_indent + self.base_indent + 'assert(handle_);\n' + \
            base_indent + self.base_indent + function[2]
        if data.copy_on_write:
            nonvirtual_member += (function[4] == 'const' and 'read().' or 'write().')
        else:
            nonvirtual_member += 'handle_->'
        nonvirtual_member += function[3] + '(' + function[1] + ' );\n' + \
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
        self.lines[self.expansion_lines[0][0]] += get_comment(self.class_indent, self.comments, function[0])
        self.lines[self.expansion_lines[0][0]] += self.class_indent + function[0] + ';'


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
            function[0].replace(function[3], data.current_struct.spelling + '::' + function[3]) + '\n' + \
            '{\n' + \
            self.base_indent + 'assert(handle_);\n' + \
            self.base_indent + function[2]
        if data.copy_on_write:
            nonvirtual_member += (function[4] == 'const' and 'read().' or 'write().')
        else:
            nonvirtual_member += 'handle_->'
        nonvirtual_member += function[3] + '(' + function[1] + ' );\n' + '}'

        self.lines[self.expansion_lines[0][0]] += nonvirtual_member


class InterfaceFileWriter(FileProcessor):
    def __init__(self, header_filename, source_filename, base_indent, handle_namespace, comments=None):
        self.header_filewriter = InterfaceHeaderFileWriter(header_filename, base_indent, handle_namespace, comments)
        self.source_filewriter = InterfaceSourceFileWriter(source_filename, base_indent, handle_namespace)

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
