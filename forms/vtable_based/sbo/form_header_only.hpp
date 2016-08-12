%struct_prefix%
{    
    using Buffer = std::array<char, %buffer_size%>;

public:
    // Contructors
    %struct_name%( ) noexcept :
        impl_ ( nullptr )
    { }

    template <typename T,
              typename std::enable_if< !std::is_same<%struct_name%, typename std::decay<T>::type>::value >::type* = nullptr>
    %struct_name% ( T&& value ) :
        vtable_ ({ 
            &type_erasure_vtable_detail::delete_impl< typename std::decay<T>::type >,
            &type_erasure_vtable_detail::clone_impl< typename std::decay<T>::type >,
            &type_erasure_vtable_detail::clone_into_buffer< typename std::decay<T>::type, Buffer >,
	    %member_function_vtable_initialization%
        }),
        impl_ ( nullptr )
    {
        if( sizeof( typename std::decay<T>::type ) <= sizeof( Buffer ) )
        {
            new (&buffer_) typename std::decay<T>::type( std::forward<T>(value) );
            impl_ = &buffer_;
        }
        else
            impl_ = new typename std::decay<T>::type( std::forward<T>(value) );
    }

    %struct_name% ( const %struct_name%& other ) :
        vtable_( other.vtable_ )
    {
        impl_ = other.clone_into( buffer_ );
    }

    %struct_name% ( %struct_name%&& other ) noexcept :
        vtable_( other.vtable_ )
    {
        if( !other.impl_ ) {
            reset( );
            impl_ = nullptr;
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

    // Assignment
    template <typename T,
              typename std::enable_if< !std::is_same<%struct_name%, typename std::decay<T>::type>::value >::type* = nullptr>
    %struct_name%& operator= ( T&& value )
    {
        return *this = %struct_name%( std::forward<T>(value) );
    }

    %struct_name%& operator= ( const %struct_name%& other )
    {
        vtable_ = other.vtable_;
        impl_ = other.clone_into( buffer_ );
        return *this;
    }

    %struct_name%& operator= ( %struct_name%&& other ) noexcept
    {
        if( !other.impl_ ) {
            reset( );
            impl_ = nullptr;
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

    ~%struct_name% ( )
    {
        reset( );
    }

    /**
     * @brief Conversion of the stored implementation to @code T*@endcode.
     * @return pointer to stored object if conversion to @code T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    T* target( ) noexcept
    {
        return type_erasure_vtable_detail::cast_impl<T>( impl_ );
    }
    
    /**
     * @brief Conversion of the stored implementation to @code const T*@endcode.
     * @return pointer to stored object if conversion to @code const T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    const T* target( ) const noexcept
    {
        return type_erasure_vtable_detail::cast_impl<T>( impl_ );
    }

    %member_functions%

private:
    void reset( ) noexcept
    {
        if( impl_ && type_erasure_vtable_detail::is_heap_allocated( impl_, buffer_ ) )
            vtable_.del( impl_ );
    }

    void* clone_into ( Buffer& buffer ) const
    {
        if( !impl_ )
            return nullptr;

        if( type_erasure_vtable_detail::heap_allocated( impl_, buffer_ ) )
            return vtable_.clone( impl_ );

        return vtable_.clone_into( impl_, buffer );
    }

    %namespace_prefix%::vtable<Buffer> vtable_;
    Buffer buffer_;
    void* impl_ = nullptr;
};


