import clang_util
import file_writer
from parser_addition import extract_include_guard
from util import trim


def find_expansion_lines_for_handle_file_writer(lines):
    retval = [0] *2
    for i in range(len(lines)):
        line = lines[i]
        try:
            pure_virtual_pos = line.index('{pure_virtual_members}')
        except:
            pure_virtual_pos = -1
        try:
            virtual_pos = line.index('{virtual_members}')
        except:
            virtual_pos = -1
        if pure_virtual_pos != -1:
            retval[0] = (i, pure_virtual_pos)
        elif virtual_pos != -1:
            retval[1] = (i, virtual_pos)
    return retval


class HandleFileWriter(file_writer.FormFileWriter):
    def __init__(self, filename, base_indent, comments=None):
        self.namespace = ''
        super(HandleFileWriter,self).__init__(filename, base_indent, comments)

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
        self.namespace = file_writer.get_handle_namespace(data)

        self.lines = map(
            lambda line: line.format(
                struct_name=data.current_struct.spelling,
                namespace_prefix=self.namespace,
                pure_virtual_members='{pure_virtual_members}',
                virtual_members='{virtual_members}'
            ),
            self.lines
        )

        self.expansion_lines = find_expansion_lines_for_handle_file_writer(self.lines)
        self.lines[self.expansion_lines[0][0]] = ''
        self.lines[self.expansion_lines[1][0]] = ''

        super(HandleFileWriter, self).process_open_class(data)

    def process_function(self, data, cursor):
        if self.lines[self.expansion_lines[1][0]] != '':
            self.lines[self.expansion_lines[1][0]] += '\n\n'
        function = clang_util.function_data(data, cursor)

        base_indent = self.base_indent + self.base_indent
        self.lines[self.expansion_lines[0][0]] += base_indent + 'virtual ' + function.signature + ' = 0;\n'
        self.lines[self.expansion_lines[1][0]] += \
            base_indent + 'virtual ' + function.signature + ' override\n' + \
            base_indent + '{\n' + \
            base_indent + self.base_indent + function.return_str + 'value_.' + function.name + '( ' + function.argument_names + ' );\n' + \
            base_indent + '}'

    def process_type_alias(self,data,cursor):
        pass

    def process_variable_declaration(self,data,cursor):
        pass

    def process_forward_declaration(self,data,cursor):
        pass
