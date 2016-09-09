#ifndef MOCK_FOOABLE_HH
#define MOCK_FOOABLE_HH

#include <array>

namespace Mock
{
    constexpr int value = 42;
    constexpr int other_value = 73;

    struct MockFooable
    {
        int foo() const
        {
            return value_;
        }

        void set_value(int val)
        {
            value_ = val;
        }

        MockFooable& operator+=(const MockFooable& other)
        {
            value_ += other.value_;
            return *this;
        }

        MockFooable operator-() const
        {
            MockFooable other;
            other.set_value( -value_ );
            return other;
        }

    private:
        int value_ = value;
    };

    struct MockLargeFooable : MockFooable
    {
    private:
        std::array<double,1024> buffer_;
    };
}

#endif // MOCK_FOOABLE_HH
