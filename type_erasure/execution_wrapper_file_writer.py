import re

import clang_util
import file_writer
import parser_addition
import util


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


class VTableExecutionWrapperFileWriter(file_writer.FormFileWriter):
    def process_open_include_guard(self, filename):
        self.include_guard = parser_addition.extract_include_guard(filename)
        if self.include_guard is None:
            return ''

        copyright_ = ''
        if util.trim(self.include_guard) != '#pragma once':
            self.include_guard = self.include_guard.replace('#ifndef ', '#ifndef EXECUTION_WRAPPER_').replace('#define ', '#define EXECUTION_WRAPPER_')
        if copyright_ != '':
            self.file_content.append(copyright)
        self.file_content.append(self.include_guard)

    def process_open_class(self, data):
        self.lines = data.handle_form_lines
        self.expansion_lines = find_expansion_lines_for_vtable_execution_wrapper_file_writer(self.lines)
        self.namespace =file_writer.get_handle_namespace(data)

        self.lines = map(
            lambda line: line.format(
                struct_name=data.current_struct.spelling,
                namespace_prefix=self.namespace,
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
        function = clang_util.function_data(data, cursor)
        base_indent = self.namespace_indent + self.base_indent

        index = function.signature.find( function.name + ' (') + len(function.name) + 1

        start_of_function_definition = base_indent + 'static ' + function.signature[:index+2] + function.const_qualifier + 'void* impl'
        if util.trim(function.argument_names) != '':
            start_of_function_definition += ', '
        else:
            start_of_function_definition += ' '

        end_of_signature = function.signature[index + 2:]
        if function.is_const:
            end_of_signature = re.sub('\)\s*const(\snoexcept)*\s*', ') noexcept', end_of_signature)

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
        if util.trim(function.argument_names) != '':
            end_of_function_definition += function.argument_names + ' '
        end_of_function_definition += ');\n' + base_indent + '}'

        self.lines[self.expansion_lines[0][0]] += end_of_function_definition
        self.lines[self.expansion_lines[1][0]] += end_of_function_definition

        function_pointer_signature = file_writer.get_execution_wrapper_function_type(function)
        function_pointer_alias = function.name + '_function_type'
        self.lines[self.expansion_lines[2][0]] += base_indent + function_pointer_alias + ' ' + function.name + ';'
        self.lines[self.expansion_lines[3][0]] += base_indent + 'using ' + function_pointer_alias + ' = ' + function_pointer_signature + ';'

    def process_type_alias(self,data,cursor):
        pass

    def process_variable_declaration(self,data,cursor):
        pass

    def process_forward_declaration(self,data,cursor):
        pass