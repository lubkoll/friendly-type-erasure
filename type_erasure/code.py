import cpp_file_parser
import parser_addition
import util

def get_decayed(type_):
    return 'typename std :: decay < ' + type_ + ' > :: type'


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


def get_handle_constructor_declaration(classname):
    return 'template < typename T , ' + enable_if_not_same(classname, 'T') + ' > ' + classname + ' ( T && value ) '


def get_handle_constructor_body_for_small_buffer_optimization(clone_into):
    return 'handle_ = type_erasure_detail :: ' + clone_into + ' < HandleBase , StackAllocatedHandle < ' + get_decayed('T') + \
           ' > , HeapAllocatedHandle < ' + get_decayed('T') + ' > > ( std :: forward < T > ( value ) , buffer_ ) ; '


def get_handle_constructor(data, classname, handle_namespace):
    constructor = get_handle_constructor_declaration(classname)
    if data.small_buffer_optimization:
        clone_into = 'clone_into_shared_ptr' if data.copy_on_write else 'clone_into'
        constructor += '{ ' + get_handle_constructor_body_for_small_buffer_optimization(clone_into) + '}'
    else:
        constructor += ': handle_ ( ' + \
                       util.get_generator(data, handle_namespace + ' :: Handle < ' + get_decayed('T') + ' > ') + ' '
        constructor += '( std :: forward < T > ( value ) ) ) { }'
    return constructor


def get_handle_assignment(data, classname, handle_namespace):
    code = 'template < typename T , ' + enable_if_not_same(classname, 'T') + ' > '
    code += classname + ' &  operator= ( T && value ) { '
    if data.small_buffer_optimization:
        clone_into = 'clone_into_shared_ptr' if data.copy_on_write else 'clone_into'
        code += 'reset ( ) ; ' + get_handle_constructor_body_for_small_buffer_optimization(clone_into)
    else:
        if data.copy_on_write:
            code += 'handle_ = '
        else:
            code += 'handle_ . reset ( '
        code += util.get_generator(data, handle_namespace + ' :: Handle < ' + get_decayed('T') + ' >  ')
        code += ' ( std :: forward < T > ( value ) ) '
        if not data.copy_on_write:
            code += ') '
        code += '; '
    return code + 'return * this ; }'


handle_copy_assignment_for_small_buffer_optimization = 'handle_ = other . handle_ ? ' \
                                                  'other . handle_ -> clone_into ( buffer_ ) : nullptr ; '


def get_cast_to_handle_base(buffer):
    return 'static_cast < HandleBase * >( static_cast < void * > ( ' + buffer + ' ) )'


def get_handle_move_assignment_for_small_buffer_optimization(escape_sequence):
    return escape_sequence + 'if ( type_erasure_detail :: is_heap_allocated ( other . handle_ , other . buffer_ ) ) ' \
           'handle_ = other . handle_ ; else { buffer_ = other.buffer_ ; ' \
           'handle_ = ' + get_cast_to_handle_base('& buffer_') + ' ; } '


def get_handle_copy_constructor(data, classname):
    declaration = classname + ' ( const ' + classname + ' & other ) '
    if data.small_buffer_optimization:
        return declaration + '{ ' + handle_copy_assignment_for_small_buffer_optimization + '}'
    return declaration + ': handle_ ( other . handle_ ? other . handle_ -> clone ( ) : nullptr ) { }'


def get_handle_move_constructor(data, classname):
    declaration = classname + ' ( ' + classname + ' && other ) noexcept '
    if data.small_buffer_optimization:
        escape_sequence = 'if ( ! other . handle_ ) return ; '
        declaration += '{ ' + get_handle_move_assignment_for_small_buffer_optimization(escape_sequence)
    else:
        declaration += ': handle_ ( std :: move ( other.handle_ ) ) { '
    return declaration + 'other . handle_ = nullptr ; }'


def get_handle_copy_operator(data, classname):
    declaration = classname + ' & operator = ( const ' + classname + ' & other ) '
    if data.small_buffer_optimization:
        declaration += '{ ' + handle_copy_assignment_for_small_buffer_optimization
    else:
        declaration += '{ handle_ . reset ( other . handle_ ? other . handle_ -> clone ( ) : nullptr ) ; '
    return declaration + 'return * this ; }'


def get_handle_move_operator(data, classname):
    declaration = classname + ' & operator = ( ' + classname + ' && other ) noexcept '
    if data.small_buffer_optimization:
        escape_sequence = 'if ( ! other . handle_ ) { handle_ = nullptr ; return * this ; }'
        declaration += '{ reset ( ) ; ' + get_handle_move_assignment_for_small_buffer_optimization(escape_sequence)
    else:
        declaration += '{ handle_ = std :: move ( other . handle_ ) ; '
    return declaration + 'other . handle_ = nullptr ; return * this ; }'


def get_operator_bool_for_member_ptr(member):
    return 'explicit operator bool ( ) const noexcept { return ' + member + ' != nullptr ; }'


def get_operator_bool_comment(declaration):
    comment = ['/**',
               ' * @brief Checks if the type-erased interface holds an implementation.',
               ' * @return true if an implementation is stored, else false',
               ' */']
    return parser_addition.Comment(comment, declaration)


def get_handle_cast(data, member, handle_namespace, const=''):
    const = const and const + ' ' or ''
    declaration = 'template < class T > ' + const + 'T * target ( ) ' + const + 'noexcept '
    if not ( not data.copy_on_write and data.small_buffer_optimization ):
        member += ' . get ( )'
    if data.small_buffer_optimization:
        return declaration + '{ if ( type_erasure_detail :: is_heap_allocated ( ' + member + ' , buffer_ ) ) ' \
                             'return type_erasure_detail :: cast < ' + const + 'T , ' + \
                             const + 'HeapAllocatedHandle < T > > ( ' + member + ' ) ; ' \
                            'return type_erasure_detail :: cast < ' + const + 'T , ' + \
                             const + 'StackAllocatedHandle < T > > ( ' + member + ' ) ; }'
    return declaration + '{ return type_erasure_detail :: cast < ' + const + 'T , ' + \
           const + handle_namespace + ' :: Handle < T > > ( ' + member + ' ) ; }'


def get_handle_cast_comment(declaration, const=''):
    comment = ['/**',
               '* @brief Conversion of the stored implementation to @code ' + const + ' T* @endcode.',
               '* @return pointer to the stored object if conversion was successful, else nullptr',
               '*/']
    return parser_addition.Comment(comment,declaration)


def get_handle_interface_function(function):
    code = util.concat(function.tokens[:cpp_file_parser.get_declaration_end_index(function.name,function.tokens)],' ')
    code += ' { assert ( handle_ ) ; ' + function.return_str + ' handle_ -> ' + function.name + ' ( '
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


def get_handle_read_function(handle_base):
    return 'const ' + handle_base + ' & read ( ) const noexcept { assert ( handle_ ) ; ' \
                                         'return * handle_ ; }'


def get_handle_write_function(data, handle_base):
    code = handle_base + ' & write ( ) { assert ( handle_ ) ; if ( ! handle_ . unique ( ) ) '
    if data.small_buffer_optimization:
        code += 'handle_ = handle_ -> clone_into ( buffer_ ) ; '
    else:
        code += 'handle_ = handle_ -> clone ( ) ; '
    return code + 'return * handle_ ; }'
