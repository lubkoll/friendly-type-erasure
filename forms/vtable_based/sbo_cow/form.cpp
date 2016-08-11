%struct_name%::%struct_name% ( ) noexcept :
    impl_ ( nullptr )
{ }

%struct_name%::%struct_name% ( const %struct_name%& other ) :
    vtable_( other.vtable_ ),
    impl_( other.impl_ )
{}

%struct_name%::%struct_name% ( %struct_name%&& other ) noexcept :
    vtable_( other.vtable_ )
{
    if( type_erasure_vtable_detail::is_heap_allocated( other.impl_.get( ), other.buffer_ ) )
        impl_ = std::move( other.impl_ );
    else
        other.vtable_.clone_into( other.impl_.get( ), buffer_, impl_ );
    other.impl_ = nullptr;
}

%struct_name%& %struct_name%::operator= ( const %struct_name%& other )
{
    vtable_ = other.vtable_;
    impl_ = other.impl_;
    return *this;
}

%struct_name%& %struct_name%::operator= ( %struct_name%&& other ) noexcept
{
    vtable_ = other.vtable_;
    if( type_erasure_vtable_detail::is_heap_allocated( other.impl_.get( ), other.buffer_ ) )
        impl_ = std::move( other.impl_ );
    else
       other.vtable_.clone_into( other.impl_.get( ), buffer_, impl_ );

    other.impl_ = nullptr;
    return *this;
}

%member_functions%

void* %struct_name%::read( ) const
{
    return impl_.get( );
}

void* %struct_name%::write( )
{
    if( !impl_.unique( ) )
    {
        if( type_erasure_vtable_detail::is_heap_allocated( impl_.get( ), buffer_) )
            vtable_.clone( impl_.get( ), impl_ );
        else
            vtable_.clone_into( impl_.get( ), buffer_, impl_ );
    }
    return impl_.get( );
}


