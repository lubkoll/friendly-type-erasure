import clang_util
import file_writer
import util


def find_expansion_lines_for_interface_file_writer(lines):
    retval = [0] * 2
    for i in range(len(lines)):
        line = lines[i]
        try:
            nonvirtual_pos = line.index('{nonvirtual_members}')
        except:
            nonvirtual_pos = -1
        try:
            type_alias_pos = line.index('{type_aliases}')
        except:
            type_alias_pos = -1

        if nonvirtual_pos != -1:
            retval[0] = (i, nonvirtual_pos)
        if type_alias_pos != -1:
            retval[1] = (i, type_alias_pos)
    return retval


class HeaderOnlyInterfaceFileWriter(file_writer.FormFileWriter):
    def __init__(self, filename, base_indent, comments=None):
        self.detail_namespace = ''
        self.lines = None
        self.expansion_lines = None
        self.type_aliases_identifier = '{type_aliases}'
        self.nonvirtual_members_identifier = '{nonvirtual_members}'
        super(HeaderOnlyInterfaceFileWriter,self).__init__(filename, base_indent, comments)

    def process_open_class(self, data):
        super(HeaderOnlyInterfaceFileWriter, self).process_open_class(data)

        self.lines = data.interface_form_lines
        self.detail_namespace = file_writer.get_detail_namespace(data)

        comment = util.get_comment('', self.comments, self.current_struct_prefix)

        if data.small_buffer_optimization:
            self.lines = map(
                lambda line: line.format(
                    buffer_size=data.buffer,
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    nonvirtual_members=self.nonvirtual_members_identifier,
                    type_aliases=self.type_aliases_identifier
                ),
                self.lines
            )
        else:
            self.lines = map(
                lambda line: line.format(
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    nonvirtual_members=self.nonvirtual_members_identifier,
                    type_aliases=self.type_aliases_identifier
                ),
                self.lines
            )

        self.expansion_lines = find_expansion_lines_for_interface_file_writer(self.lines)
        self.lines[self.expansion_lines[0][0]] = ''

    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[0][0]] == '':
            self.lines[self.expansion_lines[0][0]] += '\n\n'
        function = clang_util.function_data(data, cursor)
        base_indent = self.class_indent

        nonvirtual_member = util.get_comment(base_indent, self.comments, function.signature)
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
                if self.type_aliases_identifier in split_line:
                    continue
                if self.detail_namespace != '':
                    handle = file_writer.get_handle(split_line)
                    if handle is not None:
                        new_handle = handle.replace('Handle', self.detail_namespace + '::Handle')
                        split_line = split_line.replace(handle, new_handle)
                self.file_content.append(self.namespace_indent + split_line + '\n')

        self.lines = None
        self.expansion_lines = None


class InterfaceHeaderFileWriter(HeaderOnlyInterfaceFileWriter):
    def process_open_class(self, data):
        self.current_struct_prefix = data.current_struct_prefix
        self.open_classes += 1
        self.class_indent += self.base_indent

        self.lines = data.interface_form_lines
        self.expansion_lines = find_expansion_lines_for_interface_file_writer(self.lines)
        self.detail_namespace = file_writer.get_detail_namespace(data)

        comment = util.get_comment('', self.comments, self.current_struct_prefix)
        if data.small_buffer_optimization:
            self.lines = map(
                lambda line: line.format(
                    buffer_size=data.buffer,
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    nonvirtual_members='{nonvirtual_members}',
                    type_aliases='{type_aliases}'
                ),
                self.lines
            )
        else:
            self.lines = map(
                lambda line: line.format(
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    nonvirtual_members='{nonvirtual_members}',
                    type_aliases='{type_aliases}'
                ),
                self.lines
            )

        self.lines[self.expansion_lines[0][0]] = ''

    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[0][0]]:
            self.lines[self.expansion_lines[0][0]] += '\n\n'
        function = clang_util.function_data(data, cursor)
        self.lines[self.expansion_lines[0][0]] += util.get_comment(self.class_indent, self.comments, function.signature)
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
        self.detail_namespace = file_writer.get_detail_namespace(data)

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
        function = clang_util.function_data(data, cursor)
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


class InterfaceFileWriter(file_writer.DistributedFileWriter):
    def __init__(self, header_filename, source_filename, base_indent, comments=None):
        header_filewriter = InterfaceHeaderFileWriter(header_filename, base_indent, comments)
        source_file_writer = InterfaceSourceFileWriter(source_filename, base_indent)
        super(InterfaceFileWriter,self).__init__(header_filewriter, source_file_writer)
