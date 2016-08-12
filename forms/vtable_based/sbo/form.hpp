%struct_prefix%
{    
    using Buffer = std::array<char, %buffer_size%>;

public:
    // Contructors
    %struct_name%( ) noexcept;

    template <typename T,
              typename std::enable_if< !std::is_same<%struct_name%, typename std::decay<T>::type>::value >::type* = nullptr>
    %struct_name% ( T&& value ) :
        vtable_ ({ 
            &type_erasure_vtable_detail::delete_impl< typename std::decay<T>::type >,
            &type_erasure_vtable_detail::clone_impl< typename std::decay<T>::type >,
            &type_erasure_vtable_detail::clone_into_buffer< typename std::decay<T>::type, Buffer >,
	    %member_function_vtable_initialization%
        })
    {
        if( sizeof( typename std::decay<T>::type ) <= sizeof( Buffer ) )
        {
            new (&buffer_) typename std::decay<T>::type( std::forward<T>(value) );
            impl_ = &buffer_;
        }
        else
            impl_ = new typename std::decay<T>::type( std::forward<T>(value) );
    }

    %struct_name% ( const %struct_name%& other );

    %struct_name% ( %struct_name%&& other ) noexcept;
    // Assignment
    template <typename T,
              typename std::enable_if< !std::is_same<%struct_name%, typename std::decay<T>::type>::value >::type* = nullptr>
    %struct_name%& operator= ( T&& value )
    {
        return *this = %struct_name%( std::forward<T>(value) );
    }

    %struct_name%& operator= ( const %struct_name%& other );

    %struct_name%& operator= ( %struct_name%&& other ) noexcept;

    ~%struct_name% ( );

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
    void reset( ) noexcept;

    void* clone_into ( Buffer& buffer ) const;

    %namespace_prefix%::vtable<Buffer> vtable_;
    Buffer buffer_;
    void* impl_ = nullptr;
};


