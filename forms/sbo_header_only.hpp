%struct_prefix%
{
    using Buffer = std::array<unsigned char, %buffer_size%>;
    template <class T>
    using StackAllocatedHandle = Handle<T,Buffer,false>;
    template <class T>
    using HeapAllocatedHandle = Handle<T,Buffer,true>;

public:
    // Contructors
    %struct_name% () = default;

    template <typename T,
              typename std::enable_if<
                  !std::is_same< %struct_name%, typename std::decay<T>::type >::value
                  >::type* = nullptr>
    %struct_name% ( T&& value )
    {
        using PlainT = typename std::decay<T>::type;
        handle_ = type_erasure_detail::clone_impl< HandleBase<Buffer>, StackAllocatedHandle<PlainT>, HeapAllocatedHandle<PlainT> >( std::forward<T>(value), buffer_ );
    }

    %struct_name% ( const %struct_name%& other )
    {
        if ( other.handle_ )
            handle_ = other.handle_->clone_into( buffer_ );
    }

    %struct_name% ( %struct_name%&& other ) noexcept
    {
        swap( other.handle_, other.buffer_ );
    }

    // Assignment
    template <typename T,
              typename std::enable_if<
                  !std::is_same< %struct_name%, typename std::decay<T>::type >::value
                  >::type* = nullptr>
    %struct_name%& operator= ( T&& value )
    {
        reset( );
        using PlainT = typename std::decay<T>::type;
        handle_ = type_erasure_detail::clone_impl< HandleBase<Buffer>, StackAllocatedHandle<PlainT>, HeapAllocatedHandle<PlainT> >(std::forward<T>(value), buffer_);
        return *this;
    }

    %struct_name%& operator= ( const %struct_name%& other )
    {
        %struct_name% temp( other );
        swap( temp.handle_, temp.buffer_ );
        return *this;
    }

    %struct_name%& operator= ( %struct_name%&& other ) noexcept
    {
        %struct_name% temp( std::move( other ) );
        swap( temp.handle_, temp.buffer_ );
        return *this;
    }

    ~%struct_name% ( )
    {
        reset( );
    }

    /**
     * @brief Checks if the type-erased interface holds an implementation.
     * @return true if an implementation is stored, else false
     */
    explicit operator bool( ) const
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
        auto buffer_ptr = type_erasure_detail::get_buffer_ptr<typename std::decay<T>::type>( const_cast<Buffer&>(buffer_) );
        if( buffer_ptr )
            return type_erasure_detail::cast< T, StackAllocatedHandle<T> >( handle_ );
        return type_erasure_detail::cast< T, HeapAllocatedHandle<T> >( handle_ );
    }

    /**
     * @brief Conversion of the stored implementation to @code const T*@endcode.
     * @return pointer to stored object if conversion to @code const T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    const T* target( ) const
    {
        auto buffer_ptr = type_erasure_detail::get_buffer_ptr<typename std::decay<T>::type>( const_cast<Buffer&>(buffer_) );
        if( buffer_ptr )
            return type_erasure_detail::cast< const T, const StackAllocatedHandle<T> >( handle_ );
        return type_erasure_detail::cast< const T, const HeapAllocatedHandle<T> >( handle_ );
    }

    %nonvirtual_members%

private:
    void swap ( HandleBase<Buffer>*& other_handle, Buffer& other_buffer )
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

    void reset ( )
    {
        if ( handle_ )
            handle_->destroy( );
    }

    HandleBase<Buffer>* handle_ = nullptr;
    Buffer buffer_;
};
