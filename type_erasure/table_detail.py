import copy
import cpp_file_parser
import util


def adjust_table_arguments_tokens(classname, arguments):
    for arg in arguments:
        in_arg = False
        for token in arg.tokens:
            if token.spelling == classname:
                in_arg = True
                break
        if in_arg:
            arg.tokens = [cpp_file_parser.SimpleToken('void'),
                          cpp_file_parser.SimpleToken('*'),
                          arg.tokens[-1]]


class AddFunctionPointers(cpp_file_parser.RecursionVisitor):
    def __init__(self,data,scope):
        self.data = data
        self.scope = scope

    def visit(self,entry):
        pass

    def visit_function(self,function_):
        function = copy.deepcopy(function_)

        name = cpp_file_parser.get_function_name_for_type_erasure(function)
        function_pointer_alias = name + '_function'

        function_pointer_alias_definition = 'using ' + function_pointer_alias + ' = '
        index, offset = cpp_file_parser.find_function_name(function.name, function.tokens)
        cpp_file_parser.replace_in_tokens(function.classname, 'Interface', function.tokens[:index])
        function_pointer_alias_definition += util.concat(function.tokens[:index], ' ')
        interface_type = ('const ' if cpp_file_parser.is_const(function) else '') + self.data.interface_type + ' &'
        function_pointer_alias_definition += '( * ) ( ' + interface_type + ' , void * '

        arguments = cpp_file_parser.get_function_arguments(function)
        adjust_table_arguments_tokens(function.classname, arguments)
        for arg in arguments:
            function_pointer_alias_definition += ' , ' + arg.in_declaration()

        # Seems to be redundant, TODO Verify
        #start_index = cpp_file_parser.get_arguments_end_index(function.name, function.tokens)
        #end_index = cpp_file_parser.get_declaration_end_index(function.name, function.tokens)
        #for token in function.tokens[start_index:end_index]:
        #    if token.spelling not in ['const','noexcept']:
        #        function_pointer_alias_definition += token.spelling + ' '
        function_pointer_alias_definition += ');'

        self.scope.add(cpp_file_parser.get_alias_from_text(function_pointer_alias, function_pointer_alias_definition))
        self.scope.add(cpp_file_parser.Variable(function_pointer_alias + ' ' + name + ';'))


class AddFunctionWrappers(cpp_file_parser.RecursionVisitor):
    def __init__(self, data, scope, for_reference_wrapper=False):
        self.data = data
        self.scope = scope
        self.for_reference_wrapper = for_reference_wrapper

    def visit_function(self,function_):
        function = copy.deepcopy(function_)
        name = cpp_file_parser.get_function_name_for_type_erasure(function)
        index, offset = cpp_file_parser.find_function_name(function.name, function.tokens)
        cpp_file_parser.replace_in_tokens(function.classname, self.data.interface_type, function.tokens[:index])
        arguments = copy.deepcopy(cpp_file_parser.get_function_arguments(function))

        wrapper = 'static ' + cpp_file_parser.get_table_return_type(function)
        wrapper += name + ' ( ' +  cpp_file_parser.const_specifier(function) + self.data.interface_type + ' & ' + \
                   self.data.interface_variable + ' , '
        wrapper += ' void * impl '
        for arg in arguments:
            if cpp_file_parser.contains(function.classname, arg.tokens):
                wrapper += ' , void * ' + arg.tokens[-1].spelling
            else:
                wrapper += ' , ' + arg.in_declaration()
        wrapper += ' ) '
        if 'noexcept' in function.tokens[cpp_file_parser.get_arguments_end_index(function.name, function.tokens):
                         cpp_file_parser.get_declaration_end_index(function.name, function.tokens)]:
            wrapper += 'noexcept '

        wrapper += '{ '
        returns_class_ref = cpp_file_parser.returns_class_ref(self.data.interface_type, function)
        if not returns_class_ref:
            wrapper +=  function.return_str + ' '
        wrapper += 'static_cast '
        const = 'const ' if cpp_file_parser.is_const(function) else ''
        if self.for_reference_wrapper:
            wrapper += '< std :: reference_wrapper < Impl > * > ( impl ) -> get ( ) . '
        else:
            wrapper += '< ' + const + ' Impl * > ( impl ) -> '
        wrapper += function.name + ' ( '
        for arg in arguments:
            if cpp_file_parser.contains(function.classname, arg.tokens):
                typename = util.concat(arg.tokens[:-1], ' ')
                typename = typename.replace(' ' + function.classname + ' ', ' Impl ')

                if self.for_reference_wrapper:
                    if typename.endswith('* '):
                        wrapper += '& '
                    wrapper += 'static_cast < std :: reference_wrapper < Impl > * > ( ' + arg.in_single_function_call()
                    wrapper += ' ) -> get ( )'
                else:
                    if typename.endswith('& '):
                        wrapper += '* '
                    wrapper += 'static_cast< ' + ('const ' if cpp_file_parser.is_const(function) else '')
                    wrapper += 'Impl * > ( ' + arg.in_single_function_call() + ' )'
            else:
                wrapper += arg.in_single_function_call()
            if arg is not arguments[-1]:
                wrapper += ' ,  '
        wrapper += ' ) ; '
        if returns_class_ref:
            wrapper += 'return interface ; '
        wrapper += '}'

        self.scope.add(cpp_file_parser.get_function_from_text('execution_wrapper', name, function.return_str,
                                                              wrapper))


class AddSingleConcepts(cpp_file_parser.RecursionVisitor):
    def __init__(self, scope):
        self.scope = scope
        self.detail_namespace = 'type_erasure_table_detail'
        self.classname = ''
        self.class_concepts = []

    def visit_class(self,class_):
        self.classname = class_.get_name()
        for entry in class_.content:
            entry.visit(self)

        concept_name = class_.get_name() + '_Concept'
        class_concept = 'template < class T > using ' + concept_name + ' = std :: integral_constant < bool , '
        for concept in self.class_concepts:
            class_concept += concept + ' < type_erasure_table_detail :: remove_reference_wrapper_t < T > > :: value '
            if concept is not self.class_concepts[-1]:
                class_concept += '&& '
        class_concept += ' > ;'
        self.scope.add(cpp_file_parser.Separator())
        self.scope.add(cpp_file_parser.get_alias_from_text(concept_name, class_concept))
        self.class_concepts = []
        self.classname = ''

    def visit_function(self, function):
        function_name_for_te =  cpp_file_parser.get_function_name_for_type_erasure(function)
        try_name = 'TryMemFn_' + function_name_for_te
        try_code = 'template < class T > using ' + try_name
        try_code += ' = decltype ( std :: declval < T > ( ) . ' + function.name + ' ( '
        args = cpp_file_parser.get_function_arguments(function)
        for arg in args:
            try_code += ' std :: declval < ' + arg.decayed_type().replace(self.classname,'T') + ' > ( ) '
            if arg is not args[-1]:
                try_code += ', '
        try_code += ' )  ) ;'
        self.scope.add(cpp_file_parser.get_alias_from_text(try_name, try_code))

        has_name = 'HasMemFn_' + function_name_for_te
        template = 'template < class T , class = void > struct ' + has_name + ' : std :: false_type { } ;'
        self.scope.add(cpp_file_parser.ScopeEntry('template struct', template))
        check = self.detail_namespace + ' :: voider < ' + try_name + ' < T > > '
        specialization = 'template < class T > struct ' + has_name + ' < T , ' + check + ' > : std :: true_type { } ;'
        self.scope.add(cpp_file_parser.ScopeEntry('template specialization', specialization))
        self.class_concepts.append(has_name)


def add_table(data, scope, class_scope):
    function_table = 'template < class ' + data.interface_type
    if data.small_buffer_optimization:
        function_table += ' , class Buffer '
    function_table += '> struct ' + data.function_table_type
    scope.add(cpp_file_parser.get_template_struct_from_text(data.function_table_type, function_table))

    # default member function pointers
    if data.copy_on_write:
        clone_function = 'using clone_function = void ( * ) ( void * , std :: shared_ptr < void > & ) ;'
        scope.add(cpp_file_parser.get_alias_from_text('clone_function', clone_function))
        scope.add(cpp_file_parser.Variable('clone_function clone;'))
        if data.small_buffer_optimization:
            clone_into_function = 'using clone_into_function = ' \
                                  'void ( * ) ( void * , Buffer & , std :: shared_ptr < void > & ) ;'
            scope.add(cpp_file_parser.get_alias_from_text('clone_into_function', clone_into_function))
            scope.add(cpp_file_parser.Variable('clone_into_function clone_into;'))
    else:
        delete_function = 'using delete_function = void ( * ) ( void * ) ;'
        scope.add(cpp_file_parser.get_alias_from_text('delete_function', delete_function))
        scope.add(cpp_file_parser.Variable('delete_function del;'))
        clone_function = 'using clone_function = void * ( * ) ( void * ) ;'
        scope.add(cpp_file_parser.get_alias_from_text('clone_function', clone_function))
        scope.add(cpp_file_parser.Variable('clone_function clone;'))
        if data.small_buffer_optimization:
            clone_into_function = 'using clone_into_function = void * ( * ) ( void * , Buffer & ) ;'
            scope.add(cpp_file_parser.get_alias_from_text('clone_into_function', clone_into_function))
            scope.add(cpp_file_parser.Variable('clone_into_function clone_into;'))

    # interface-related function pointers
    class_scope.visit(AddFunctionPointers(data, scope))
    scope.close()


class SortTable(cpp_file_parser.RecursionVisitor):
    def visit_class(self,class_object):
        aliases = []
        variables = []
        for entry in class_object.content:
            aliases.append(entry) if cpp_file_parser.is_alias(entry) else variables.append(entry)

        class_object.content = aliases
        if class_object.content:
            class_object.content.append(cpp_file_parser.Separator())
        class_object.content.extend(variables)

    def visit_template_class(self, class_object):
        self.visit_class(class_object)


def add_execution_wrapper(data, scope, class_scope):
    execution_wrapper = 'template < class Interface , class Impl > struct execution_wrapper'
    scope.add(cpp_file_parser.get_template_struct_from_text('execution_wrapper', execution_wrapper))
    class_scope.visit(AddFunctionWrappers(data, scope))
    scope.close()

    # template specialization for std::reference_wrapper
    execution_wrapper = 'template < class Interface , class Impl > struct execution_wrapper ' \
                        '< Interface , std :: reference_wrapper < Impl > >'
    scope.add(cpp_file_parser.get_template_struct_from_text('execution_wrapper', execution_wrapper))
    class_scope.visit(AddFunctionWrappers(data, scope, for_reference_wrapper=True))
    scope.close()

    # concepts
    class_scope.visit(AddSingleConcepts(scope))