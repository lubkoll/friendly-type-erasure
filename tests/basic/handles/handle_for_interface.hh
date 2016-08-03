#pragma once

#include <functional>
#include <memory>
#include <type_traits>
#include <utility>

#include "util.hh"
namespace Basic
{    
    namespace Fooable_impl
    {
        struct HandleBase
        {
            virtual ~HandleBase () = default;
            virtual HandleBase* clone () const = 0;
            virtual int foo ( ) const = 0;
            virtual void set_value ( int value ) = 0;
        };
    
    
        template <typename T>
        struct Handle : HandleBase
        {
            template <typename U,
                      typename std::enable_if< std::is_same< typename std::remove_const<T>::type, 
    	                                                 typename std::decay<U>::type& >::value >::type* = nullptr >
            explicit Handle( U&& value ) noexcept
                : value_( std::forward<U>(value) )
            {}
    
            template <typename U,
                      typename std::enable_if< std::is_same< T, typename std::decay<U>::type >::value >::type* = nullptr >
            explicit Handle( U&& value ) noexcept ( std::is_rvalue_reference< decltype(value) >::value &&
                                                    std::is_nothrow_move_constructible<typename std::decay<U>::type>::value )
                : value_( std::forward<U>(value) )
            {}
    
            virtual HandleBase* clone () const
            {
                return new Handle(value_);
            }
    
            virtual int foo ( ) const override
            {
                return value_.foo( );
            }

            virtual void set_value ( int value ) override
            {
                value_.set_value(value );
            }
    
            T value_;
        };
    
    
        template <typename T>
        struct Handle< std::reference_wrapper<T> > : Handle<T&>
        {
            Handle (std::reference_wrapper<T> ref)
                : Handle<T&> (ref.get())
            {}
        };
    }
    
}

