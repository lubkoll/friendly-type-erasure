namespace %namespace_prefix%
{
    template <class Buffer>
    struct HandleBase
    {
        virtual ~HandleBase ( ) = default;
        virtual HandleBase* clone_into( Buffer & buf ) const = 0;
        virtual bool unique( ) const = 0;
        virtual void add_ref( ) = 0;
        virtual void destroy( ) = 0;
        %pure_virtual_members%
    };

    template <class T, class Buffer, bool HeapAllocated>
    struct Handle : HandleBase< Buffer >
    {
        template <typename U,
                  typename std::enable_if<
                      !std::is_same< T, typename std::decay<U>::type >::value
                                           >::type* = nullptr>
        explicit Handle ( U&& value ) noexcept :
            value_( value ),
            ref_count_( 1 )
        {}

        template <typename U,
                  typename std::enable_if<
                      std::is_same< T, typename std::decay<U>::type >::value
                                           >::type* = nullptr>
        explicit Handle ( U&& value ) noexcept ( std::is_rvalue_reference<U>::value &&
                                                 std::is_nothrow_move_constructible<typename std::decay<U>::type>::value ) :
            value_( std::forward<U>( value ) ),
            ref_count_( 1 )
        {}

        HandleBase<Buffer>* clone_into ( Buffer& buffer ) const override
        { 
            return type_erasure_detail::clone_impl< HandleBase<Buffer>, Handle<T,Buffer,false>, Handle<T,Buffer,true> >( value_, buffer ); 
        }

        bool unique ( ) const override
        { 
            return ref_count_ == 1u; 
        }

        void add_ref ( ) override
        { 
            ++ref_count_; 
        }

        void destroy ( ) override
        {
            if ( ref_count_ == 1u ) {
                if ( HeapAllocated )
                    delete this;
                else
                    this->~Handle();
            } else {
                --ref_count_;
            }
        }

        %virtual_members%

        T value_;
        std::atomic_size_t ref_count_;
    };

    template <class T, class Buffer, bool HeapAllocated>
    struct Handle<std::reference_wrapper<T>, Buffer, HeapAllocated> : Handle<T&, Buffer, HeapAllocated>
    {
        Handle ( std::reference_wrapper<T> ref ) :
            Handle<T&, Buffer, HeapAllocated> ( ref.get( ) )
        {}
    };
}
