#ifndef COW_FOOABLE_HH
#define COW_FOOABLE_HH

#include "handles/handle_for_interface.hh"

namespace COW
{    
    class Fooable
    {
    public:
        // Contructors
        Fooable () = default;
    
        template <typename T,
                  typename std::enable_if<
                      !std::is_same< Fooable, typename std::decay<T>::type >::value
                      >::type* = nullptr>
        Fooable (T&& value) :
            handle_ (
                std::make_shared< Fooable_impl::Handle<typename std::decay<T>::type> >(
                    std::forward<T>(value)
                )
            )
        {}
    
        // Assignment
        template <typename T,
                  typename std::enable_if<
                      !std::is_same< Fooable, typename std::decay<T>::type >::value
                      >::type* = nullptr>
        Fooable& operator= (T&& value)
        {
            Fooable temp( std::forward<T>(value) );
            std::swap(temp.handle_, handle_);
            return *this;
        }
    
        /**
         * @brief Checks if the type-erased interface holds an implementation.
         * @return true if an implementation is stored, else false
         */
        explicit operator bool() const
        {
            return handle_ != nullptr;
        }
    
        /**
         * @brief Conversion of the stored implementation to @code T*@endcode.
         * @return pointer to stored object if conversion to @code T*@endcode
         *         was successful, else nullptr
         */
        template <typename T>
        T* target() noexcept
        {
    	return type_erasure_detail::cast< T, Fooable_impl::Handle<T> >( handle_.get() );
        }
    
        /**
         * @brief Conversion of the stored implementation to @code const T*@endcode.
         * @return pointer to stored object if conversion to @code const T*@endcode
         *         was successful, else nullptr
         */
        template <typename T>
        const T* target() const noexcept
        {
    	return type_erasure_detail::cast< const T, const Fooable_impl::Handle<T> >( handle_.get() );
        }
    
        int foo ( ) const
        {
            assert(handle_);
            return read().foo( );
        }
    
        void set_value ( int value )
        {
            assert(handle_);
            write().set_value(value );
        }
    
    private:
        const Fooable_impl::HandleBase& read () const
        {
            return *handle_;
        }
    
        Fooable_impl::HandleBase& write ()
        {
            if (!handle_.unique())
                handle_ = handle_->clone();
            return *handle_;
        }
    
        std::shared_ptr<Fooable_impl::HandleBase> handle_;
    };
}

#endif
