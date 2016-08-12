namespace %namespace_prefix%
{
    struct HandleBase
    {
        virtual ~HandleBase () = default;
        virtual std::shared_ptr<HandleBase> clone () const = 0;
        %pure_virtual_members%
    };


    template <typename T>
    struct Handle : HandleBase
    {
        template <typename U,
                  typename std::enable_if< std::is_same< typename std::remove_const<T>::type, 
	                                                 typename std::decay<U>::type& >::value >::type* = nullptr >
        explicit Handle( U&& value ) noexcept( type_erasure_detail::is_nothrow_constructible<U>( ) )
            : value_( std::forward<U>(value) )
        {}

        template <typename U,
                  typename std::enable_if< std::is_same< T, typename std::decay<U>::type >::value >::type* = nullptr >
        explicit Handle( U&& value ) noexcept( type_erasure_detail::is_nothrow_constructible<U>( ) )
            : value_( std::forward<U>(value) )
        {}

        std::shared_ptr<HandleBase> clone () const override
        {
            return std::make_shared<Handle>(value_);
        }

        %virtual_members%

        T value_;
    };


    template <typename T>
    struct Handle< std::reference_wrapper<T> > : Handle<T&>
    {
        Handle (std::reference_wrapper<T> ref) noexcept
            : Handle<T&> (ref.get())
        {}
    };
}

