%struct_name%::%struct_name% ( const %struct_name%& other )
{
    if ( other.handle_ )
        handle_ = other.handle_->clone_into( buffer_ );
}

%struct_name%::%struct_name% ( %struct_name%&& other ) noexcept
{
    swap( other.handle_, other.buffer_ );
}

%struct_name%& %struct_name%::operator= ( const %struct_name%& other )
{
    %struct_name% temp( other );
    swap( temp.handle_, temp.buffer_ );
    return *this;
}

%struct_name%& %struct_name%::operator= ( %struct_name%&& other ) noexcept
{
    %struct_name% temp( std::move( other ) );
    swap( temp.handle_, temp.buffer_ );
    return *this;
}

%struct_name%::~%struct_name% ( )
{
    reset( );
}

%struct_name%::operator bool( ) const noexcept
{
    return handle_ != nullptr;
}

%nonvirtual_members%

void %struct_name%::swap ( HandleBase<Buffer>*& other_handle, Buffer& other_buffer ) noexcept
{
    using namespace type_erasure_detail;
    const auto this_heap_allocated = !handle_ || handle_->heap_allocated();
    const auto other_heap_allocated = !other_handle || other_handle->heap_allocated();

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

void %struct_name%::reset ( ) noexcept
{
    if ( handle_ )
        handle_->destroy( );
}
