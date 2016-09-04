    // %<int.hh>%
    struct Int;

    /**
     * @brief class Fooable
     */
    class Fooable
    {
    public:
        /// void type
        typedef void void_type;
        using type = int;
        static const int static_value = 1;

        enum class Enum { BLUB };

        explicit Fooable( int value ) : value_(value)
        { 
        }

        /// Does something.
        int foo() const
        {
          return value_.value;
        }

        //! Retrieves something else.
        void set_value(int value)
        { value_ = value; }

    private:
       Pimpl::Int value_ = static_value;
    };

