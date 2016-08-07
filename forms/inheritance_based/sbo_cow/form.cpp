%struct_name%::%struct_name% ( const %struct_name%& other ) :
    handle_ (
        !other.handle_ || type_erasure_detail::heap_allocated( other.handle_, other.buffer_ ) ?
        other.handle_ :
        type_erasure_detail::handle_ptr< HandleBase<Buffer> >(
            type_erasure_detail::char_ptr( &buffer_ ) + type_erasure_detail::handle_offset( other.handle_, other.buffer_ )
        )
    ),
    buffer_ ( other.buffer_)
{
    if ( handle_ )
        handle_->add_ref( );
}

%struct_name%::%struct_name% ( %struct_name%&& other ) noexcept
{
    swap( other.handle_, other.buffer_ );
}

%struct_name%& %struct_name%::operator= ( const %struct_name%& other )
{
    %struct_name% temp( other );
    swap( temp.handle_, temp.buffer_ );
    if ( handle_ )
        handle_->add_ref( );
    return *this;
}

%struct_name%& %struct_name%::operator= ( %struct_name%&& other ) noexcept
{
    %struct_name% temp( std::move( other ) );
    swap( temp.handle_, temp.buffer_ );
    return *this;
}

%struct_name%::~%struct_name% ()
{
    reset();
}

%struct_name%::operator bool( ) const
{
    return handle_ != nullptr;
}

%nonvirtual_members%

void %struct_name%::swap ( HandleBase<Buffer>*& other_handle, Buffer& other_buffer )
{
    using namespace type_erasure_detail;
    const auto this_heap_allocated = heap_allocated( handle_, buffer_ );
    const auto other_heap_allocated = heap_allocated( other_handle, other_buffer );

    if ( this_heap_allocated && other_heap_allocated ) {
        std::swap( handle_, other_handle );
    } else if ( this_heap_allocated ) {
        const auto offset = handle_offset( other_handle, other_buffer );
        other_handle = handle_;
        buffer_ = other_buffer;
        handle_ = handle_ptr< HandleBase<Buffer> >( char_ptr(&buffer_) + offset );
    } else if ( other_heap_allocated ) {
        const auto offset = handle_offset( handle_, buffer_ );
        handle_ = other_handle;
        other_buffer = buffer_;
        other_handle = handle_ptr< HandleBase<Buffer> >( char_ptr(&other_buffer) + offset );
    } else {
        const auto this_offset = handle_offset( handle_, buffer_ );
        const auto other_offset = handle_offset( other_handle, other_buffer );
        std::swap( buffer_, other_buffer );
        handle_ = handle_ptr< HandleBase<Buffer> >( char_ptr(&buffer_) + this_offset );
        other_handle = handle_ptr< HandleBase<Buffer> >( char_ptr(&other_buffer) + other_offset );
    }
}

void %struct_name%::reset ( )
{
    if ( handle_ )
        handle_->destroy( );
}

const HandleBase<%struct_name%::Buffer>& %struct_name%::read ( ) const
{
    return *handle_;
}

HandleBase<%struct_name%::Buffer>& %struct_name%::write ( )
{
    if ( !handle_->unique( ) )
        handle_ = handle_->clone_into( buffer_ );
    return *handle_;
}
