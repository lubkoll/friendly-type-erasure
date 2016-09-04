import cpp_file_parser
import parser_addition
import util


FUNCTION_TABLE_TYPE = 'FunctionTable'
FUNCTION_TABLE = 'function_table'
IMPL           = 'impl'
HANDLE         = 'handle_'


def get_decayed(type_):
    return 'typename std :: decay < ' + type_ + ' > :: type'


def get_return_type(data, classname):
    if data.copy_on_write:
        return 'std :: shared_ptr < HandleBase > '
    else:
        return classname + ' * '


def get_generator(data, classname):
    if data.copy_on_write:
        return 'std :: make_shared < typename std :: decay < ' + classname + ' > :: type >'
    else:
        return 'new typename std :: decay < ' + classname + ' > :: type'


static_reference_check = 'typename std :: enable_if < std :: is_same < typename std :: remove_const < T > :: type , ' + \
                         get_decayed('U') + ' & > :: value > :: type * = nullptr '


def get_static_value_check(first_type, second_type):
    return 'typename std :: enable_if < std :: is_same < ' + first_type + ' , ' + get_decayed(second_type) + \
           ' > :: value > :: type * = nullptr'

def enable_if_not_same(first_type, second_type):
    return 'typename std :: enable_if < ! std :: is_same < ' + first_type + ' , ' + get_decayed(second_type) + \
           ' > :: value > :: type * = nullptr'

noexcept_if_nothrow_constructible = 'noexcept ( type_erasure_detail :: is_nothrow_constructible < U > ( ) )'


def get_default_default_constructor(classname, noexcept='', constexpr=''):
    return (constexpr and constexpr + ' ' or '') + classname + ' ( ) ' + (noexcept and noexcept + ' ' or '')  + '= default ;'


def get_constructor_from_value_declaration(classname):
    return 'template < typename T , ' + enable_if_not_same(classname, 'T') + ' > ' + classname + ' ( T && value ) '


def get_handle_constructor_body_for_small_buffer_optimization(clone_into):
    return '' + HANDLE + ' = type_erasure_detail :: ' + clone_into + ' < HandleBase , StackAllocatedHandle < ' + get_decayed('T') + \
           ' > , HeapAllocatedHandle < ' + get_decayed('T') + ' > > ( std :: forward < T > ( value ) , buffer_ ) ; '


def get_handle_constructor(data, classname, handle_namespace):
    constructor = get_constructor_from_value_declaration(classname)
    if data.small_buffer_optimization:
        clone_into = 'clone_into_shared_ptr' if data.copy_on_write else 'clone_into'
        constructor += '{ ' + get_handle_constructor_body_for_small_buffer_optimization(clone_into) + '}'
    else:
        constructor += ': ' + HANDLE + ' ( ' + \
                       get_generator(data, handle_namespace + ' :: Handle < ' + get_decayed('T') + ' > ') + ' '
        constructor += '( std :: forward < T > ( value ) ) ) { }'
    return constructor


def get_assignment_from_value(data, classname, handle_namespace):
    code = 'template < typename T , ' + enable_if_not_same(classname, 'T') + ' > '
    code += classname + ' &  operator= ( T && value ) { '

    if data.table:
        return code + 'return * this = ' + classname + ' ( std :: forward < T > ( value ) ) ; }'

    if data.small_buffer_optimization:
        clone_into = 'clone_into_shared_ptr' if data.copy_on_write else 'clone_into'
        if not data.copy_on_write:
            code += 'reset ( ) ; '
        code += get_handle_constructor_body_for_small_buffer_optimization(clone_into)
    else:
        if data.copy_on_write:
            code += HANDLE + ' = '
        else:
            code += '' + HANDLE + ' . reset ( '
        code += get_generator(data, handle_namespace + ' :: Handle < ' + get_decayed('T') + ' >  ')
        code += ' ( std :: forward < T > ( value ) ) '
        if not data.copy_on_write:
            code += ') '
        code += '; '
    return code + 'return * this ; }'


handle_copy_assignment_for_small_buffer_optimization = HANDLE + ' = other . ' + HANDLE + ' ? ' \
                                                  'other . ' + HANDLE + ' -> clone_into ( buffer_ ) : nullptr ; '


def get_cast_to_handle_base(buffer):
    return 'static_cast < HandleBase * >( static_cast < void * > ( ' + buffer + ' ) )'


def get_handle_move_assignment_for_small_buffer_optimization(escape_sequence):
    return escape_sequence + 'if ( type_erasure_detail :: is_heap_allocated ( other . ' + HANDLE + ' , other . buffer_ ) ) ' +\
           HANDLE + ' = other . ' + HANDLE + ' ; else { buffer_ = other.buffer_ ; ' +\
           HANDLE + ' = ' + get_cast_to_handle_base('& buffer_') + ' ; } '


def get_copy_constructor_for_table(data, classname, impl=IMPL, function_table=FUNCTION_TABLE):
    declaration = classname + ' ( const ' + classname + ' & other ) : ' + function_table + ' ( other . '
    declaration += FUNCTION_TABLE + ' ) '
    if data.small_buffer_optimization:
        if data.copy_on_write:
            return declaration + ', ' + impl + ' ( other . ' + impl + ' ) { }'
        else:
            return declaration + '{ ' + impl + ' = other . clone_into ( buffer_ ) ; }'
    else:
        declaration += ' , ' + impl + ' ( other . ' + impl + ' ? other . ' + function_table + ' . clone ( other . ' + impl + ' ) '
        return declaration + ': nullptr ) { }'


def get_copy_constructor_for_handle(data, classname, member):
    declaration = classname + ' ( const ' + classname + ' & other ) '
    if data.small_buffer_optimization:
        return declaration + '{ ' + handle_copy_assignment_for_small_buffer_optimization + '}'
    return declaration + ': ' + member + ' ( other . ' + member + ' ? other . ' + member + ' -> clone ( ) : nullptr ) { }'


def get_pimpl_copy_constructor(data, classname, private_classname, member):
    declaration = classname + ' ( const ' + classname + ' & other ) '
    if data.small_buffer_optimization:
        return declaration + '{ ' + handle_copy_assignment_for_small_buffer_optimization + '}'
    return declaration + ': ' + member + ' ( other . ' + member + ' ? new ' + private_classname + ' ( * other . pimpl_ ) : ' \
                                                                                                  'nullptr ) { }'


def get_pimpl_move_constructor(data, classname, member):
    declaration = classname + ' ( ' + classname + ' && other ) '
    if data.small_buffer_optimization:
        return declaration + '{ ' + handle_copy_assignment_for_small_buffer_optimization + '}'
    return declaration + ': ' + member + ' ( std::move( other ) . ' + member + ' ) { }'


def get_pimpl_copy_assignment(data, classname, private_classname, member):
    declaration = classname + ' & ' + 'operator = ( const ' + classname + ' & other ) { '
    if data.small_buffer_optimization:
        declaration += handle_copy_assignment_for_small_buffer_optimization
    declaration += 'if ( other . ' + member + ' ) '
    return declaration + member + ' . reset ( new ' + private_classname + '( * other . pimpl_ ) ) ; ' \
                                                                          'else pimpl_ = nullptr ; return * this ; }'


def get_pimpl_move_assignment(data, classname, member):
    declaration = classname + ' & ' + 'operator = ( ' + classname + ' && other ) { '
    if data.small_buffer_optimization:
        declaration += handle_copy_assignment_for_small_buffer_optimization
    return declaration + member + ' = std::move( other ) . ' + member + ' ; return * this ; }'


def get_copy_constructor(data, classname, impl=IMPL, function_table=FUNCTION_TABLE):
    return get_copy_constructor_for_table(data, classname, impl, function_table ) if data.table \
            else get_copy_constructor_for_handle(data, classname, impl)


def get_move_constructor_for_table(data, classname, impl=IMPL, function_table=FUNCTION_TABLE):
    declaration = classname + ' ( ' + classname + ' && other ) noexcept : '
    declaration += function_table + ' ( other . ' + function_table + ' ) '
    if data.small_buffer_optimization:
        if data.copy_on_write:
            declaration += '{ if ( type_erasure_vtable_detail :: is_heap_allocated ( other . ' + impl + ' . get ( ) , '
            declaration += 'other . buffer_ ) ) ' + impl + ' = std :: move ( other . ' + impl + ' ) ;'
            declaration += 'else other . ' + function_table + ' . clone_into ( other . ' + impl + ' . get ( ) , '
            return declaration + ' buffer_ , ' + impl + ' ) ; other . ' + impl + ' = nullptr ; }'
        else:
            declaration += '{ if ( ! other . ' + impl + ' ) { reset ( ) ; ' + impl + ' = nullptr ; return ; } '
            declaration += 'if ( type_erasure_vtable_detail :: is_heap_allocated ( other . ' + impl + ' , other . buffer_ ) ) '
            declaration += impl + ' = other . ' + impl + ' ; '
            declaration += 'else { buffer_ = std :: move ( other . buffer_ ) ; ' + impl + ' = & buffer_ ; } '
            return declaration + 'other . ' + impl + ' = nullptr ; }'
    else:
        declaration += ' , ' + impl + ' ( other . ' + impl + ' ) '
        return declaration + '{ other . ' + impl + ' = nullptr ; }'


def get_move_constructor_for_handle(data, classname, handle=HANDLE):
    declaration = classname + ' ( ' + classname + ' && other ) noexcept '
    if data.small_buffer_optimization:
        escape_sequence = 'if ( ! other . ' + handle + ' ) return ; '
        declaration += '{ ' + get_handle_move_assignment_for_small_buffer_optimization(escape_sequence)
    else:
        declaration += ': ' + handle + ' ( std :: move ( other.' + handle + ' ) ) { '
    return declaration + 'other . ' + handle + ' = nullptr ; }'


def get_move_constructor(data, classname, impl=IMPL, function_table=FUNCTION_TABLE):
    return get_move_constructor_for_table(data, classname, impl, function_table) if data.table \
            else get_move_constructor_for_handle(data, classname, impl)


def get_copy_operator_for_handle(data, classname, handle=HANDLE):
    declaration = classname + ' & operator = ( const ' + classname + ' & other ) '
    if data.small_buffer_optimization:
        declaration += '{ ' + handle_copy_assignment_for_small_buffer_optimization
    else:
        declaration += '{ ' + handle + ' . reset ( other . ' + handle + ' ? other . ' + handle + ' -> clone ( ) : nullptr ) ; '
    return declaration + 'return * this ; }'


def get_copy_operator_for_table(data, classname, impl=IMPL, function_table=FUNCTION_TABLE):
    declaration = classname + ' & operator = ( const ' + classname + ' & other ) { '
    declaration += function_table + ' = other . ' + function_table + ' ; '
    if data.small_buffer_optimization:
        if data.copy_on_write:
            declaration += impl + ' = other . ' + impl + ' ; '
        else:
            declaration += impl + ' = other . clone_into ( buffer_ ) ; '
    else:
        declaration += impl + ' = other . ' + impl + ' ? other . ' + function_table + ' . clone ( other . ' + impl + ' ) '
        declaration += ': nullptr ;'
    return declaration + 'return * this ; }'


def get_copy_operator(data, classname, impl=IMPL, function_table=FUNCTION_TABLE):
    return get_copy_operator_for_table(data, classname, impl, function_table) if data.table \
        else get_copy_operator_for_handle(data, classname, impl)


def get_move_operator_for_table(data, classname, impl=IMPL, function_table=FUNCTION_TABLE):
    declaration = classname + ' & operator = ( ' + classname + ' && other ) noexcept { '
    if data.small_buffer_optimization:
        if data.copy_on_write:
            declaration += function_table + ' = other . ' + function_table + ' ; '
            declaration += 'if ( type_erasure_vtable_detail :: is_heap_allocated ( other . ' + impl + ' .  get ( ) , '
            declaration += 'other . buffer_ ) ) ' + impl + ' = std :: move ( other . ' + impl + ' ) ; '
            declaration +='else other . ' + function_table + ' . clone_into ( other . ' + impl + ' . get ( ) , '
            declaration += 'buffer_ , ' + impl + ' ) ;'
        else:
            declaration += 'if ( ! other . ' + impl + ' ) { reset ( ) ; ' + impl + ' = nullptr ; return * this ; } '
            declaration += function_table + ' = other . ' + function_table + ' ; '
            declaration += 'if ( type_erasure_vtable_detail :: is_heap_allocated ( other . ' + impl + ' , other . buffer_ ) ) '
            declaration += impl + ' = other . ' + impl + ' ; '
            declaration += 'else { buffer_ = std :: move ( other . buffer_ ) ; ' + impl + ' = & buffer_ ; } '
    else:
        declaration += function_table + ' = other . ' + function_table + ' ; '
        declaration += impl + ' = other . ' + impl + ' ; '
    declaration += 'other . ' + impl + ' = nullptr ; '
    return declaration + 'return * this ; }'


def get_move_operator_for_handle(data, classname, handle=HANDLE):
    declaration = classname + ' & operator = ( ' + classname + ' && other ) noexcept '
    if data.small_buffer_optimization:
        escape_sequence = 'if ( ! other . ' + handle + ' ) { ' + handle + ' = nullptr ; return * this ; }'
        declaration += '{ reset ( ) ; ' + get_handle_move_assignment_for_small_buffer_optimization(escape_sequence)
    else:
        declaration += '{ ' + handle + ' = std :: move ( other . ' + handle + ' ) ; '
    return declaration + 'other . ' + handle + ' = nullptr ; return * this ; }'


def get_move_operator(data, classname, impl=IMPL, function_table=FUNCTION_TABLE):
    return get_move_operator_for_table(data, classname, impl, function_table) if data.table \
        else get_move_operator_for_handle(data, classname, impl)


def get_operator_bool_for_member_ptr(member):
    return 'explicit operator bool ( ) const noexcept { return ' + member + ' != nullptr ; }'


def get_operator_bool_comment(declaration):
    comment = ['/**\n',
               ' * @brief Checks if the type-erased interface holds an implementation.\n',
               ' * @return true if an implementation is stored, else false\n',
               ' */\n']
    return parser_addition.Comment(comment, declaration)


def get_cast(data, member, handle_namespace, const=''):
    const = const and const + ' ' or ''
    declaration = 'template < class T > ' + const + 'T * target ( ) ' + const + 'noexcept '
    if not ( not data.copy_on_write and data.small_buffer_optimization ) and not data.table:
        member += ' . get ( )'

    if data.table:
         declaration += '{ return type_erasure_vtable_detail :: cast_impl < T > ( '
         declaration += 'read ( )' if data.copy_on_write else member
         return declaration + ' ) ; }'
    else:
        if data.small_buffer_optimization:
            return declaration + '{ if ( type_erasure_detail :: is_heap_allocated ( ' + member + ' , buffer_ ) ) ' \
                                 'return type_erasure_detail :: cast < ' + const + 'T , ' + \
                                 const + 'HeapAllocatedHandle < T > > ( ' + member + ' ) ; ' \
                                'return type_erasure_detail :: cast < ' + const + 'T , ' + \
                                 const + 'StackAllocatedHandle < T > > ( ' + member + ' ) ; }'
    return declaration + '{ return type_erasure_detail :: cast < ' + const + 'T , ' + \
           const + handle_namespace + ' :: Handle < T > > ( ' + member + ' ) ; }'


def get_handle_cast_comment(declaration, const=''):
    comment = ['/**\n',
               '* @brief Conversion of the stored implementation to @code ' + const + ' T* @endcode.\n',
               '* @return pointer to the stored object if conversion was successful, else nullptr\n',
               '*/\n']
    return parser_addition.Comment(comment,declaration)


def get_handle_interface_function(function):
    code = util.concat(function.tokens[:cpp_file_parser.get_declaration_end_index(function.name,function.tokens)],' ')
    code += ' { assert ( ' + HANDLE + ' ) ; ' + function.return_str + ' ' + HANDLE + ' -> ' + function.name + ' ( '
    arguments = cpp_file_parser.get_function_arguments(function)
    for arg in arguments:
        code += arg.in_single_function_call()
        if arg is not arguments[-1]:
            code += ' , '
    return code + ' ) ; }'


def get_handle_specialization(data):
    if data.small_buffer_optimization:
        return 'template < class T , class Buffer , bool HeapAllocated > ' \
               'struct Handle < std :: reference_wrapper < T > , Buffer , HeapAllocated > : ' \
               'Handle < T & , Buffer , HeapAllocated > { ' \
               'Handle ( std :: reference_wrapper < T > ref ) noexcept : ' \
               'Handle < T & , Buffer , HeapAllocated > ( ref . get ( ) ) { } ' \
               '};'
    return 'template < typename T > struct Handle < std :: reference_wrapper < T > > : Handle < T & > { ' \
           'Handle ( std :: reference_wrapper < T > ref ) noexcept : Handle < T & > ( ref . get ( ) ) { } } ;'


def get_read_function_for_handle(return_type, member):
    return return_type + ' read ( ) const noexcept { assert ( ' + member + ' ) ; ' \
                                         'return * ' + member + ' ; }'


def get_read_function_for_table(return_type, member):
    return return_type + ' read ( ) const noexcept { assert ( ' + member + ' ) ; return ' + member + ' . get ( ) ; }'


def get_read_function(data, return_type, member):
    return get_read_function_for_table(return_type, member) if data.table \
        else get_read_function_for_handle(return_type, member)


def get_write_function_for_handle(data, return_type, member):
    code = return_type + ' write ( ) { assert ( ' + member + ' ) ; if ( ! ' + member + ' . unique ( ) ) '
    if data.small_buffer_optimization:
        code += member + ' = ' + member + ' -> clone_into ( buffer_ ) ; '
    else:
        code += member + ' = ' + member + ' -> clone ( ) ; '
    return code + 'return * ' + member + ' ; }'


def get_write_function_for_table(data, return_type, member, function_table):
    code = return_type + ' write ( ) { if ( ! ' + member + ' . unique ( ) ) '
    if data.small_buffer_optimization:
        code += '{ if ( type_erasure_vtable_detail :: is_heap_allocated ( ' + member + ' . get ( ) , buffer_ ) ) '
        code += function_table + ' . clone( ' + member + ' . get ( ) , ' + member + ' ) ; '
        code += 'else ' + function_table + ' . clone_into ( ' + member + ' . get ( ) , buffer_ , ' + member + ' ) ; }'
    else:
        code += function_table + ' . clone ( read ( ) , ' + member + ' ) ; '
    return code + 'return ' + member + ' . get ( ) ; }'


def get_write_function(data, return_type, member, function_table=FUNCTION_TABLE):
    return get_write_function_for_table(data, return_type, member, function_table) if data.table \
        else get_write_function_for_handle(data, return_type, member)


def get_single_function_call(function):
    return function.name + ' ( ' + cpp_file_parser.get_function_arguments_in_single_call(function) + ' ) '
