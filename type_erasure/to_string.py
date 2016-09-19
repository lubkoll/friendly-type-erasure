import util
import cpp_file_parser


class Visitor(cpp_file_parser.Visitor):
    def __init__(self, short_entries=[]):
        self.short_entries = short_entries

    def visit(self,visited):
        return str(visited) + '\n'

    def visit_alias(self,alias):
        return util.concat(alias.tokens, ' ') + '\n' + ('' if cpp_file_parser.ALIAS in self.short_entries else '\n')

    def visit_class(self,class_object):
        code = ''
        for token in class_object.get_tokens():
            if token.spelling == ';':
                return code + token.spelling
            if token.spelling == '{':
                break
            code += token.spelling + ' '
#        str = class_.type + ' ' + class_.name + '{\n'
        code += '\n{\n'
        for entry in class_object.content:
            code += entry.visit(self)
        code += '};\n'
        return code + ('' if cpp_file_parser.CLASS in self.short_entries else '\n')

    def visit_template_class(self,template_class):
        code = util.concat(template_class.tokens,' ') + '{ '
        for entry in template_class.content:
            code += entry.visit(self)
        return code + '};\n' + ('' if cpp_file_parser.CLASS_TEMPLATE in self.short_entries else '\n')

    def visit_namespace(self,namespace):
        str = ''
        if namespace.name != 'global':
            str = '\nnamespace ' + namespace.name + '\n{'
        for entry in namespace.content:
            str += entry.visit(self)
        if namespace.name != 'global':
            str += '}'
        return str + ('' if cpp_file_parser.NAMESPACE in self.short_entries else '\n')

    def visit_inclusion_directive(self,inclusion_directive):
        return '#include ' + inclusion_directive.value + ('' if cpp_file_parser.INCLUSION_DIRECTIVE in self.short_entries else '\n')

    def visit_access_specifier(self,access_specifier):
        return access_specifier.value + ':\n'

    def visit_comment(self,comment):
        str = ''
        for line in comment.value.comment:
            str += line
        return str


class VisitorForHeaderFile(Visitor):
    def visit_static_variable(self,variable):
        return self.visit(variable)

    def visit_function(self, function):
        code = function.get_declaration() + ';\n'
        return code + ('' if cpp_file_parser.FUNCTION in self.short_entries else '\n')

    def visit_template_function(self, function):
       return function.get_in_place_definition() + ('' if cpp_file_parser.FUNCTION_TEMPLATE in self.short_entries else '\n')

    def visit_namespace(self, namespace):
        code = ''
        if namespace.name != 'global':
            code = '\nnamespace ' + namespace.name
            code += '\n{\n'

        for entry in namespace.content:
            code += entry.visit(self)
        if namespace.name != 'global':
            code += '}'
        return code + ('' if cpp_file_parser.NAMESPACE in self.short_entries else '\n')

    def visit_comment(self,comment):
        first_line = comment.value.comment[0]
        if first_line.startswith('//') and not first_line.startswith('///') and not first_line.startswith('//!'):
            return ''
        else:
            return super(VisitorForHeaderFile,self).visit_comment(comment)


class VisitorForSourceFile(Visitor):
    def __init__(self, new_line='\n'):
        self.current_class = None
        self.current_class_aliases = []
        super(VisitorForSourceFile,self).__init__(new_line)

    def add_class_prefix_for_nested_types(self, function):
        for token in function.tokens:
            if token.spelling in self.current_class_aliases:
                token.spelling = self.current_class + '::' + token.spelling

    def remove_class_prefix_for_nested_types(self, function):
        for token in function.tokens:
            for alias in self.current_class_aliases:
                if token.spelling == self.current_class + '::' + alias:
                    token.spelling = alias

    def visit_function(self, function):
        if cpp_file_parser.is_deleted(function) or cpp_file_parser.is_defaulted(function) or cpp_file_parser.is_constexpr(function):
            return ''

        self.add_class_prefix_for_nested_types(function)

        definition = function.get_definition() + '\n'
        keywords_to_remove = ['explicit ', 'constexpr ']
        while definition.split(' ')[0] in keywords_to_remove:
            definition = definition[len(definition.split(' ')[0]) + 1:]

        self.remove_class_prefix_for_nested_types(function)

        return definition

    def visit_forward_declaration(self,forward_declaration):
        return ''

    def visit_template_function(self,function):
        return ''

    def visit_variable(self,variable):
        return ''

    def visit_static_variable(self,variable):
        return ''

    def visit_alias(self,alias):
        return ''

    def visit_enum(self,enum):
        return ''

    def visit_access_specifier(self,access_specifier):
        return ''

    def visit_class(self,class_):
        if cpp_file_parser.is_forward_declaration(class_):
            return util.concat(class_.tokens, ' ')cd
        str = ''
        self.current_class = class_.get_name( )
        for entry in class_.content:
            if entry.type == cpp_file_parser.ALIAS:
                self.current_class_aliases.append(entry.name)

        for entry in class_.content:
            str += entry.visit(self)

        self.current_class = None
        self.current_class_aliases = []
        return str

    def visit_comment(self,comment):
        return ''


def write_scope(scope, filename, visitor=Visitor(), write_warning_header=True):
    file = open(filename,'w')
    if write_warning_header:
        file.write(util.do_not_overwrite_text)
    file.write(scope.visit(visitor))
    file.close()
