%struct_name%::%struct_name% ( ) noexcept 
{ }

%struct_name%::%struct_name% ( const %struct_name%& other ) :
    vtable_( other.vtable_ )
{
    impl_ = other.clone_into( buffer_ );
}

%struct_name%::%struct_name% ( %struct_name%&& other ) noexcept :
    vtable_( other.vtable_ )
{
    if( !other.impl_ ) {
        reset( );
        return;
    }

    if( type_erasure_vtable_detail::is_heap_allocated( other.impl_, other.buffer_ ) )
        impl_ = other.impl_;
    else
    {
        buffer_ = std::move( other.buffer_ );
        impl_ = &buffer_;
    }

    other.impl_ = nullptr;
}

%struct_name%& %struct_name%::operator= ( const %struct_name%& other )
{
    vtable_ = other.vtable_;
    impl_ = other.clone_into( buffer_ );
    return *this;
}

%struct_name%& %struct_name%::operator= ( %struct_name%&& other ) noexcept
{
    if( !other.impl_ ) {
        reset( );
        return *this;
    }

    vtable_ = other.vtable_;
    if( type_erasure_vtable_detail::is_heap_allocated( other.impl_, other.buffer_ ) )
        impl_ = other.impl_;
    else
    {
        buffer_ = std::move( other.buffer_ );
        impl_  = &buffer_;
    }

    other.impl_ = nullptr;

    return *this;
}

%struct_name%::~%struct_name% ( )
{
    if( impl_ && type_erasure_vtable_detail::is_heap_allocated( impl_, buffer_ ) )
        vtable_.del( impl_ );
}

%struct_name%::operator bool( ) const noexcept
{
    return impl_ != nullptr;
}

%member_functions%

void %struct_name%::reset( ) noexcept
{
    impl_ = nullptr;
}

void* %struct_name%::clone_into ( %struct_name%::Buffer& buffer ) const
{
    if( !impl_ )
        return nullptr;

    if( type_erasure_vtable_detail::is_heap_allocated( impl_, buffer_ ) )
        return vtable_.clone( impl_ );

    return vtable_.clone_into( impl_, buffer );
}
