#include <gtest/gtest.h>

#include "interface.hh"
#include "../mock_fooable.hh"

namespace
{
    using SBOHeaderOnly::Fooable;
    using Mock::MockFooable;
    using Mock::MockLargeFooable;

    void death_tests( Fooable& fooable )
    {
#ifndef NDEBUG
        EXPECT_DEATH( fooable.foo(), "" );
        EXPECT_DEATH( fooable.set_value( Mock::other_value ), "" );
#endif
    }

    void test_interface( Fooable& fooable, int initial_value, int new_value )
    {
        EXPECT_EQ( fooable.foo(), initial_value );
        fooable.set_value( new_value );
        EXPECT_EQ( fooable.foo(), new_value );
    }

    void test_ref_interface( Fooable& fooable, const MockFooable& mock_fooable,
                             int new_value )
    {
        test_interface(fooable, mock_fooable.foo(), new_value);
        EXPECT_EQ( mock_fooable.foo(), new_value );
    }

    void test_copies( Fooable& copy, const Fooable& fooable, int new_value )
    {
        auto value = fooable.foo();
        test_interface( copy, value, new_value );
        EXPECT_EQ( fooable.foo(), value );
        ASSERT_NE( value, new_value );
        EXPECT_NE( fooable.foo(), copy.foo() );
    }
}


TEST( TestHeaderOnlySBOFooable, Empty )
{
    Fooable fooable;
    death_tests(fooable);

    Fooable copy(fooable);
    death_tests(copy);

    Fooable move( std::move(fooable) );
    death_tests(move);

    Fooable copy_assign;
    copy_assign = move;
    death_tests(copy_assign);

    Fooable move_assign;
    move_assign = std::move(fooable);
    death_tests(move_assign);
}


TEST( TestHeaderOnlySBOFooable, CopyFromValue_SmallObject )
{
    MockFooable mock_fooable;
    auto value = mock_fooable.foo();
    Fooable fooable( mock_fooable );

    test_interface( fooable, value, Mock::other_value );
}

TEST( TestHeaderOnlySBOFooable, CopyFromValue_LargeObject )
{
    MockLargeFooable mock_fooable;
    auto value = mock_fooable.foo();
    Fooable fooable( mock_fooable );

    test_interface( fooable, value, Mock::other_value );
}


TEST( TestHeaderOnlySBOFooable, CopyConstruction_SmallObject )
{
    Fooable fooable = MockFooable();
    Fooable other( fooable );
    test_copies( other, fooable, Mock::other_value );
}

TEST( TestHeaderOnlySBOFooable, CopyConstruction_LargeObject )
{
    Fooable fooable = MockLargeFooable();
    Fooable other( fooable );
    test_copies( other, fooable, Mock::other_value );
}


TEST( TestHeaderOnlySBOFooable, CopyFromValueWithReferenceWrapper_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable( std::ref(mock_fooable) );

    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}


TEST( TestHeaderOnlySBOFooable, CopyFromValueWithReferenceWrapper_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable( std::ref(mock_fooable) );

    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}


TEST( TestHeaderOnlySBOFooable, MoveFromValue_SmallObject )
{
    MockFooable mock_fooable;
    auto value = mock_fooable.foo();
    Fooable fooable( std::move(mock_fooable) );

    test_interface( fooable, value, Mock::other_value );
}
TEST( TestHeaderOnlySBOFooable, MoveFromValue_LargeObject )
{
    MockLargeFooable mock_fooable;
    auto value = mock_fooable.foo();
    Fooable fooable( std::move(mock_fooable) );

    test_interface( fooable, value, Mock::other_value );
}


TEST( TestHeaderOnlySBOFooable, MoveConstruction_SmallObject )
{
    Fooable fooable = MockFooable();
    auto value = fooable.foo();
    Fooable other( std::move(fooable) );

    test_interface( other, value, Mock::other_value );
    death_tests(fooable);
}

TEST( TestHeaderOnlySBOFooable, MoveConstruction_LargeObject )
{
    Fooable fooable = MockLargeFooable();
    auto value = fooable.foo();
    Fooable other( std::move(fooable) );

    test_interface( other, value, Mock::other_value );
    death_tests(fooable);
}


TEST( TestHeaderOnlySBOFooable, MoveFromValueWithReferenceWrapper_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable( std::move(std::ref(mock_fooable)) );

    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}

TEST( TestHeaderOnlySBOFooable, MoveFromValueWithReferenceWrapper_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable( std::move(std::ref(mock_fooable)) );

    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}


TEST( TestHeaderOnlySBOFooable, CopyAssignFromValue_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable;

    auto value = mock_fooable.foo();
    fooable = mock_fooable;
    test_interface(fooable, value, Mock::other_value);
}

TEST( TestHeaderOnlySBOFooable, CopyAssignFromValue_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable;

    auto value = mock_fooable.foo();
    fooable = mock_fooable;
    test_interface(fooable, value, Mock::other_value);
}


TEST( TestHeaderOnlySBOFooable, CopyAssignment_SmallObject )
{
    Fooable fooable = MockFooable();
    Fooable other;
    other = fooable;
    test_copies( other, fooable, Mock::other_value );
}

TEST( TestHeaderOnlySBOFooable, CopyAssignment_LargeObject )
{
    Fooable fooable = MockLargeFooable();
    Fooable other;
    other = fooable;
    test_copies( other, fooable, Mock::other_value );
}


TEST( TestHeaderOnlySBOFooable, CopyAssignFromValueWithReferenceWrapper_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable;

    fooable = std::ref(mock_fooable);
    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}

TEST( TestHeaderOnlySBOFooable, CopyAssignFromValueWithReferenceWrapper_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable;

    fooable = std::ref(mock_fooable);
    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}


TEST( TestHeaderOnlySBOFooable, MoveAssignFromValue_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable;

    auto value = mock_fooable.foo();
    fooable = std::move(mock_fooable);
    test_interface(fooable, value, Mock::other_value);
}

TEST( TestHeaderOnlySBOFooable, MoveAssignFromValue_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable;

    auto value = mock_fooable.foo();
    fooable = std::move(mock_fooable);
    test_interface(fooable, value, Mock::other_value);
}


TEST( TestHeaderOnlySBOFooable, MoveAssignment_SmallObject )
{
    Fooable fooable = MockFooable();
    auto value = fooable.foo();
    Fooable other;
    other = std::move(fooable);

    test_interface( other, value, Mock::other_value );
    death_tests(fooable);
}

TEST( TestHeaderOnlySBOFooable, MoveAssignment_LargeObject )
{
    Fooable fooable = MockLargeFooable();
    auto value = fooable.foo();
    Fooable other;
    other = std::move(fooable);

    test_interface( other, value, Mock::other_value );
    death_tests(fooable);
}


TEST( TestHeaderOnlySBOFooable, MoveAssignFromValueWithReferenceWrapper_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable;

    fooable = std::move(std::ref(mock_fooable));
    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}

TEST( TestHeaderOnlySBOFooable, MoveAssignFromValueWithReferenceWrapper_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable;

    fooable = std::move(std::ref(mock_fooable));
    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}


TEST( TestHeaderOnlySBOFooable, Cast_SmallObject )
{
    Fooable fooable = MockFooable();

    EXPECT_TRUE( fooable.target<int>() == nullptr );
    ASSERT_FALSE( fooable.target<MockFooable>() == nullptr );

    fooable.set_value(Mock::other_value);
    EXPECT_EQ( fooable.target<MockFooable>()->foo(), Mock::other_value );
}

TEST( TestHeaderOnlySBOFooable, Cast_LargeObject )
{
    Fooable fooable = MockLargeFooable();

    EXPECT_TRUE( fooable.target<int>() == nullptr );
    ASSERT_FALSE( fooable.target<MockLargeFooable>() == nullptr );

    fooable.set_value(Mock::other_value);
    EXPECT_EQ( fooable.target<MockLargeFooable>()->foo(), Mock::other_value );
}


TEST( TestHeaderOnlySBOFooable, ConstCast_SmallObject )
{
    const Fooable fooable = MockFooable();

    EXPECT_TRUE( fooable.target<int>() == nullptr );
    ASSERT_FALSE( fooable.target<MockFooable>() == nullptr );

    EXPECT_EQ( fooable.target<MockFooable>()->foo(), Mock::value );
}

TEST( TestHeaderOnlySBOFooable, ConstCast_LargeObject )
{
    const Fooable fooable = MockLargeFooable();

    EXPECT_TRUE( fooable.target<int>() == nullptr );
    ASSERT_FALSE( fooable.target<MockLargeFooable>() == nullptr );

    EXPECT_EQ( fooable.target<MockLargeFooable>()->foo(), Mock::value );
}
