// copy
// right
#pragma once

#include "handles/handle_for_interface.hh"

namespace Basic
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
        Fooable ( T&& value ) :
            handle_ (
                new Fooable_impl::Handle<typename std::decay<T>::type>(
                    std::forward<T>( value )
                )
            )
        {}
    
        Fooable ( const Fooable & rhs )
            : handle_ ( rhs.handle_ ? rhs.handle_->clone() : nullptr )
        {}
    
        Fooable ( Fooable&& rhs ) noexcept
            : handle_ ( std::move(rhs.handle_) )
        {}
    
        // Assignment
        template <typename T,
                  typename std::enable_if<
                      !std::is_same< Fooable, typename std::decay<T>::type >::value
                      >::type* = nullptr>
        Fooable& operator= (T&& value)
        {
            Fooable temp( std::forward<T>( value ) );
            std::swap(temp, *this);
            return *this;
        }
    
        Fooable& operator= (const Fooable& rhs)
        {
            Fooable temp(rhs);
            std::swap(temp, *this);
            return *this;
        }
    
        Fooable& operator= (Fooable&& rhs) noexcept
        {
            handle_ = std::move(rhs.handle_);
            return *this;
        }
    
        /**
         * @brief Checks if the type-erased interface holds an implementation.
         * @return true if an implementation is stored, else false
         */
        explicit operator bool() const noexcept
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
            return handle_->foo( );
        }
    
        void set_value ( int value )
        {
            assert(handle_);
            handle_->set_value(value );
        }
    
    private:
        std::unique_ptr<Fooable_impl::HandleBase> handle_;
    };
}

