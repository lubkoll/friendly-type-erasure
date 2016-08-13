import clang_util
import file_writer
import util


def find_expansion_lines_for_vtable_interface_file_writer(lines):
    retval = [0] * 3
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
        try:
            type_aliases_pos = line.index('{type_aliases}')
        except:
            type_aliases_pos = -1

        if member_function_vtable_initialization_pos != -1:
            retval[0] = (i, member_function_vtable_initialization_pos)
        if member_functions_pos != -1:
            retval[1] = (i, member_functions_pos)
        if type_aliases_pos != -1:
            retval[1] = (i, type_aliases_pos)
    return retval


class HeaderOnlyVTableInterfaceFileWriter(file_writer.CppFileWriter):
    def __init__(self, filename, base_indent, comments=None):
        self.detail_namespace = ''
        self.lines = None
        self.expansion_lines = None
        self.namespace = ''
        self.vtable_initialization_identifier = '{member_function_vtable_initialization}'
        self.member_function_identifier = '{member_functions}'
        self.type_aliases_identifier = '{type_aliases}'
        super(HeaderOnlyVTableInterfaceFileWriter,self).__init__(filename, base_indent, comments)

    def process_open_class(self, data):
        super(HeaderOnlyVTableInterfaceFileWriter, self).process_open_class(data)
        self.namespace = file_writer.get_detail_namespace(data)
        self.lines = data.interface_form_lines
        self.expansion_lines = find_expansion_lines_for_vtable_interface_file_writer(self.lines)

        comment = util.get_comment('', self.comments, self.current_struct_prefix)

        if data.small_buffer_optimization:
            self.lines = map(
                lambda line: line.format(
                    buffer_size=data.buffer,
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    namespace_prefix=self.namespace,
                    member_function_vtable_initialization=self.vtable_initialization_identifier,
                    member_functions=self.member_function_identifier,
                    type_aliases=self.type_aliases_identifier
                ),
                self.lines
            )
        else:
            self.lines = map(
                lambda line: line.format(
                    struct_prefix=comment + data.current_struct_prefix,
                    struct_name=data.current_struct.spelling,
                    namespace_prefix=self.namespace,
                    member_function_vtable_initialization=self.vtable_initialization_identifier,
                    member_functions=self.member_function_identifier,
                    type_aliases=self.type_aliases_identifier
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
        function = clang_util.function_data(data, cursor)
        base_indent = self.class_indent

        self.lines[self.expansion_lines[0][0]] += base_indent + 2*self.base_indent + \
                                                  '&' + self.namespace + '::execution_wrapper< typename std::decay<T>::type >::' + function.name
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
            if self.type_aliases_identifier in line:
                continue
            split_lines = line.split('\n')
            for split_line in split_lines:
                self.file_content.append(self.namespace_indent + split_line + '\n')

        self.lines = None
        self.expansion_lines = None

        super(HeaderOnlyVTableInterfaceFileWriter,self).process_close_class()

    def process_type_alias(self,data,cursor):
        if self.expansion_lines is None:
            super(HeaderOnlyVTableInterfaceFileWriter,self).process_type_alias(data, cursor)
            return
        if self.expansion_lines[1][0] == -1:
            return
        alias_or_typedef = clang_util.get_type_alias_or_typedef(data.tu, cursor)
        comment = util.get_comment(self.base_indent, self.comments, alias_or_typedef)
        if '{type_aliases}' in self.lines[self.expansion_lines[1][0]]:
            self.lines[self.expansion_lines[1][0]] = comment
        else:
            self.lines[self.expansion_lines[1][0]] += comment
        self.lines[self.expansion_lines[1][0]] += self.class_indent + alias_or_typedef

    def process_variable_declaration(self,data,cursor):
        if self.expansion_lines is None :
            super(HeaderOnlyVTableInterfaceFileWriter,self).process_variable_declaration(data, cursor)
            return
        if self.expansion_lines[1][0] == -1:
            return
        variable_declaration = clang_util.get_variable_declaration(data.tu, cursor)
        comment = util.get_comment(self.base_indent, self.comments, variable_declaration)
        if '{type_aliases}' in self.lines[self.expansion_lines[1][0]]:
            self.lines[self.expansion_lines[1][0]] = comment
        else:
            self.lines[self.expansion_lines[1][0]] += comment
        self.lines[self.expansion_lines[1][0]] += self.class_indent + variable_declaration


class VTableInterfaceHeaderFileWriter(HeaderOnlyVTableInterfaceFileWriter):
    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[0][0]] != '':
            self.lines[self.expansion_lines[0][0]] += ',\n'
        if self.lines[self.expansion_lines[1][0]] != '':
            self.lines[self.expansion_lines[1][0]] += '\n\n'
        function = clang_util.function_data(data, cursor)
        base_indent = self.class_indent

        self.lines[self.expansion_lines[0][0]] += \
            base_indent + 2*self.base_indent + '&' + self.namespace + \
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
        function = clang_util.function_data(data, cursor)
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


class VTableInterfaceFileWriter(file_writer.DistributedFileWriter):
    def __init__(self, header_filename, source_filename, base_indent, comments=None):
        header_filewriter = VTableInterfaceHeaderFileWriter(header_filename, base_indent, comments)
        source_file_writer = VTableInterfaceSourceFileWriter(source_filename, base_indent)
        super(VTableInterfaceFileWriter,self).__init__(header_filewriter, source_file_writer)