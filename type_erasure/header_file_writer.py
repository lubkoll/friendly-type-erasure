from util import open_namespace, close_namespace, add_include_guard, close_include_guard, add_headers, trim


def find_expansion_lines(self, lines):
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


class HandleFileWriter:
    def __init__(self, file_name, basic_indent, comments=None):
        self.file_name = file_name
        self.file = None
        self.basic_indent = basic_indent
        self.namespace_indent = ''
        self.comments = comments
        self.include_guard = ''

    def open(self):
        self.file = open(self.file_name,'w')

    def close(self):
        self.file.write('\n')
        self.file.close()

    def add_include_guard(self, filename):
        self.include_guard = add_include_guard(self.file, filename, self.comments)

    def close_include_guard(self):
        close_include_guard(self.file, self.include_guard)

    def add_headers(self, headers):
        add_headers(self.file, headers)

    def open_namespace(self, name):
        open_namespace(self.file, name, self.namespace_indent)
        self.namespace_indent += self.basic_indent

    def close_namespace(self):
        close_namespace(self.file, self.namespace_indent)
        self.namespace_indent -= self.basic_indent

    def add_class(self, data):
        lines = data.handle_form_lines

        expansion_lines = find_expansion_lines(lines)
        base_indent = self.namespace_indent + self.basic_indent
        indent = base_indent + self.basic_indent

        lines = map(
            lambda line: line.format(
                struct_name=data.current_struct.spelling,
                namespace_prefix='{namespace_prefix}',
                pure_virtual_members='{pure_virtual_members}',
                virtual_members='{virtual_members}'
            ),
            lines
        )

        pure_virtual_members = ''
        virtual_members = ''

        for function in data.member_functions:
            pure_virtual_members += \
                base_indent + 'virtual ' + function[0] + ' = 0;\n'

            virtual_members += \
                base_indent + 'virtual ' + function[0] + ' override\n' + \
                base_indent + '{\n' + \
                indent + function[2] + 'value_.' + function[3] + '(' + function[1] + ' );\n' + \
                base_indent + '}\n'
            if function is data.member_functions[-1]:
                pass
            else:
                virtual_members += '\n'

        pure_virtual_members = pure_virtual_members[:-1]
        virtual_members = virtual_members[:-1]

        lines[expansion_lines[0][0]] = "namespace " + data.handle_namespace
        lines[expansion_lines[1][0]] = pure_virtual_members
        lines[expansion_lines[2][0]] = virtual_members

        for line in lines:
            if trim(include_guard) not in line:
                self.file.write(line + '\n')