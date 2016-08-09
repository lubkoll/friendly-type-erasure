%struct_prefix%
{
public:
    // Contructors
    constexpr %struct_name% ( ) noexcept = default;

    template <typename T,
              typename std::enable_if<
                  !std::is_same< %struct_name%, typename std::decay<T>::type >::value
                  >::type* = nullptr>
    %struct_name%( T&& value ) :
        handle_ (
            new Handle< typename std::decay<T>::type >(
                std::forward<T>( value )
            )
        )
    {}

    %struct_name%( const %struct_name% & rhs );

    %struct_name%( %struct_name%&& rhs ) noexcept;

    // Assignment
    template <typename T,
              typename std::enable_if<
                  !std::is_same< %struct_name%, typename std::decay<T>::type >::value
                  >::type* = nullptr>
    %struct_name%& operator=( T&& value )
    {
        %struct_name% temp( std::forward<T>( value ) );
        std::swap(temp, *this);
        return *this;
    }

    %struct_name%& operator=( const %struct_name%& rhs );

    %struct_name%& operator=( %struct_name%&& rhs ) noexcept;

    /**
     * @brief Checks if the type-erased interface holds an implementation.
     * @return true if an implementation is stored, else false
     */
    explicit operator bool( ) const noexcept;

    /**
     * @brief Conversion of the stored implementation to @code T*@endcode.
     * @return pointer to stored object if conversion to @code T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    T* target( ) noexcept
    {
        return type_erasure_detail::cast< T, Handle<T> >( handle_.get( ) );
    }

    /**
     * @brief Conversion of the stored implementation to @code const T*@endcode.
     * @return pointer to stored object if conversion to @code const T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    const T* target( ) const noexcept
    {
        return type_erasure_detail::cast< const T, const Handle<T> >( handle_.get( ) );
    }

    %nonvirtual_members%

private:
    std::unique_ptr< HandleBase > handle_;
};
