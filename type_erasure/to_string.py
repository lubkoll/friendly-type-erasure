import util


class Visitor(object):
    def to_string(self,visited):
        return str(visited) + '\n'

    def function_to_string(self,function):
        return self.to_string(function)

    def class_to_string(self,class_):
        str = class_.type + ' ' + class_.name + '{\n'
        for entry in class_.content:
            str += entry.to_string_visit(self)
        str += '};\n'
        return str

    def template_class_to_string(self,template_class):
        code = util.concat(template_class.tokens,' ') + '{\n'
        for entry in template_class.content:
            code += entry.to_string_visit(self)
        return code + '};\n'

    def namespace_to_string(self,namespace):
        str = ''
        if namespace.name != 'global':
            str = '\nnamespace ' + namespace.name + '\n{\n'
        for entry in namespace.content:
            str += entry.to_string_visit(self)
        if namespace.name != 'global':
            str += '}\n'
        return str

    def inclusion_directive_to_string(self,inclusion_directive):
        return '#include ' + inclusion_directive.value + '\n'

    def access_specifier_to_string(self,access_specifier):
        return access_specifier.value + ':'


class VisitorForHeaderFile(Visitor):
    def __init__(self, comments=None):
        self.comments = comments

    def function_to_string(self, function):
        code = function.get_declaration()
        if self.comments:
            comment = util.get_comment(self.comments,code)
            code = comment + code
        return code + '\n'

    def class_to_string(self, class_object):
        code = class_.type + ' ' + class_object.name
        if self.comments:
            comment = util.get_comment(self.comments,code)
            code = comment + code

        code += '\n{\n'
        for entry in class_object.content:
            code += entry.to_string_visit(self)
        code += '};\n'
        return code

    def namespace_to_string(self, namespace):
        code = ''
        if namespace.name != 'global':
            code = '\nnamespace ' + namespace.name
            if self.comments:
                comment = util.get_comment(self.comments,code)
                code = comment + code
            code += '\n{\n'

        for entry in namespace.content:
            code += entry.to_string_visit(self)
        if namespace.name != 'global':
            code += '}\n'
        return code


class VisitorForSourceFile(Visitor):
    def function_to_string(self, function):
        return function.get_definition() + '\n'


def write_scope(scope, filename, visitor=Visitor()):
    file = open(filename,'w')
    file.write(scope.to_string_visit(visitor))
    file.close()
