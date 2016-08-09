%struct_prefix%
{
    using Buffer = std::array<char, %buffer_size%>;
    template <class T>
    using StackAllocatedHandle = Handle<T, Buffer, false>;
    template <class T>
    using HeapAllocatedHandle = Handle<T, Buffer, true>;

public:
    %struct_name% ( ) noexcept = default;

    // Constructors
    template <typename T,
              typename std::enable_if<
                  !std::is_same< %struct_name%, typename std::decay<T>::type >::value
                  >::type* = nullptr>
    %struct_name% (T&& impl)
    {
        using PlainT = typename std::decay<T>::type;
        handle_ = type_erasure_detail::clone_impl< HandleBase<Buffer>, StackAllocatedHandle<PlainT>, HeapAllocatedHandle<PlainT> >( std::forward<T>(impl), buffer_ );
    }

    %struct_name% ( const %struct_name%& other ) :
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

    %struct_name% ( %struct_name%&& other ) noexcept
    {
        swap( other.handle_, other.buffer_ );
    }

    // Assignments
    template <typename T,
              typename std::enable_if<
                  !std::is_same< %struct_name%, typename std::decay<T>::type >::value
                  >::type* = nullptr>
    %struct_name%& operator= ( T&& impl )
    {
        reset( );
        using PlainT = typename std::decay<T>::type;
        handle_ = type_erasure_detail::clone_impl< HandleBase<Buffer>, StackAllocatedHandle<PlainT>, HeapAllocatedHandle<PlainT> >( std::forward<T>(impl), buffer_ );
        return *this;
    }

    %struct_name%& operator= ( const %struct_name%& other )
    {
        %struct_name% temp( other );
        swap( temp.handle_, temp.buffer_ );
        if ( handle_ )
            handle_->add_ref( );
        return *this;
    }

    %struct_name%& operator= ( %struct_name%&& other ) noexcept
    {
        %struct_name% temp( std::move( other ) );
        swap( temp.handle_, temp.buffer_ );
        return *this;
    }

    ~%struct_name% ()
    {
        reset();
    }

    /**
     * @brief Checks if the type-erased interface holds an implementation.
     * @return true if an implementation is stored, else false
     */
    explicit operator bool( ) const noexcept
    {
        return handle_ != nullptr;
    }

    /**
     * @brief Conversion of the stored implementation to @code T*@endcode.
     * @return pointer to stored object if conversion to @code T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    T* target( )
    {
        assert( handle_ );
        void* buffer_ptr = type_erasure_detail::get_buffer_ptr<typename std::decay<T>::type>( const_cast<Buffer&>(buffer_) );
        if( buffer_ptr )
        {
            auto handle = dynamic_cast<StackAllocatedHandle<T>*>( handle_ );
            if( handle )
                return &handle->value_;
        }
        else
        {
            auto handle = dynamic_cast<HeapAllocatedHandle<T>*>( handle_ );
            if( handle )
                return &handle->value_;
        }

        return nullptr;
    }

    /**
     * @brief Conversion of the stored implementation to @code const T*@endcode.
     * @return pointer to stored object if conversion to @code const T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    const T* target() const
    {
        assert( handle_ );
        void* buffer_ptr = type_erasure_detail::get_buffer_ptr<typename std::decay<T>::type>( const_cast<Buffer&>(buffer_) );
        if( buffer_ptr )
        {
            auto handle = dynamic_cast<StackAllocatedHandle<T>*>(handle_);
            if( handle )
                return &handle->value_;
        }
        else
        {
            auto handle = dynamic_cast<HeapAllocatedHandle<T>*>(handle_);
            if( handle )
                return &handle->value_;
        }

        return nullptr;
    }

    %nonvirtual_members%

private:
    void swap ( HandleBase<Buffer>*& other_handle, Buffer& other_buffer ) noexcept
    {
        using namespace type_erasure_detail;
        const bool this_heap_allocated = heap_allocated( handle_, buffer_ );
        const bool other_heap_allocated = heap_allocated( other_handle, other_buffer );

        if ( this_heap_allocated && other_heap_allocated ) {
            std::swap( handle_, other_handle );
        } else if ( this_heap_allocated ) {
            const std::ptrdiff_t offset = handle_offset( other_handle, other_buffer );
            other_handle = handle_;
            buffer_ = other_buffer;
            handle_ = handle_ptr< HandleBase<Buffer> >( char_ptr(&buffer_) + offset );
        } else if ( other_heap_allocated ) {
            const std::ptrdiff_t offset = handle_offset( handle_, buffer_ );
            handle_ = other_handle;
            other_buffer = buffer_;
            other_handle = handle_ptr< HandleBase<Buffer> >( char_ptr(&other_buffer) + offset );
        } else {
            const std::ptrdiff_t this_offset = handle_offset( handle_, buffer_ );
            const std::ptrdiff_t other_offset = handle_offset( other_handle, other_buffer );
            std::swap( buffer_, other_buffer );
            handle_ = handle_ptr< HandleBase<Buffer> >( char_ptr(&buffer_) + this_offset );
            other_handle = handle_ptr< HandleBase<Buffer> >( char_ptr(&other_buffer) + other_offset );
        }
    }

    void reset ( ) noexcept
    {
        if ( handle_ )
            handle_->destroy( );
    }

    const HandleBase<Buffer>& read ( ) const noexcept
    {
        return *handle_;
    }

    HandleBase<Buffer> & write ( )
    {
        if ( !handle_->unique( ) )
            handle_ = handle_->clone_into( buffer_ );
        return *handle_;
    }

    HandleBase<Buffer>* handle_ = nullptr;
    Buffer buffer_;
};
