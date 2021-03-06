#include <gtest/gtest.h>

#include "interface.hh"
#include "../mock_fooable.hh"

namespace
{
    using VTableSBOCOW::Fooable;
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


TEST( TestVTableSBOCOWFooable, Empty )
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


TEST( TestVTableSBOCOWFooable, CopyFromValue_SmallObject )
{
    MockFooable mock_fooable;
    auto value = mock_fooable.foo();
    Fooable fooable( mock_fooable );

    test_interface( fooable, value, Mock::other_value );
}

TEST( TestVTableSBOCOWFooable, CopyFromValue_LargeObject )
{
    MockLargeFooable mock_fooable;
    auto value = mock_fooable.foo();
    Fooable fooable( mock_fooable );

    test_interface( fooable, value, Mock::other_value );
}


TEST( TestVTableSBOCOWFooable, CopyConstruction_SmallObject )
{
    Fooable fooable = MockFooable();
    Fooable other( fooable );
    test_copies( other, fooable, Mock::other_value );
}

TEST( TestVTableSBOCOWFooable, CopyConstruction_LargeObject )
{
    Fooable fooable = MockLargeFooable();
    Fooable other( fooable );
    test_copies( other, fooable, Mock::other_value );
}


TEST( TestVTableSBOCOWFooable, CopyFromValueWithReferenceWrapper_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable( std::ref(mock_fooable) );

    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}


TEST( TestVTableSBOCOWFooable, CopyFromValueWithReferenceWrapper_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable( std::ref(mock_fooable) );

    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}


TEST( TestVTableSBOCOWFooable, MoveFromValue_SmallObject )
{
    MockFooable mock_fooable;
    auto value = mock_fooable.foo();
    Fooable fooable( std::move(mock_fooable) );

    test_interface( fooable, value, Mock::other_value );
}
TEST( TestVTableSBOCOWFooable, MoveFromValue_LargeObject )
{
    MockLargeFooable mock_fooable;
    auto value = mock_fooable.foo();
    Fooable fooable( std::move(mock_fooable) );

    test_interface( fooable, value, Mock::other_value );
}


TEST( TestVTableSBOCOWFooable, MoveConstruction_SmallObject )
{
    Fooable fooable = MockFooable();
    auto value = fooable.foo();
    Fooable other( std::move(fooable) );

    test_interface( other, value, Mock::other_value );
    death_tests(fooable);
}

TEST( TestVTableSBOCOWFooable, MoveConstruction_LargeObject )
{
    Fooable fooable = MockLargeFooable();
    auto value = fooable.foo();
    Fooable other( std::move(fooable) );

    test_interface( other, value, Mock::other_value );
    death_tests(fooable);
}


TEST( TestVTableSBOCOWFooable, MoveFromValueWithReferenceWrapper_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable( std::move(std::ref(mock_fooable)) );

    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}

TEST( TestVTableSBOCOWFooable, MoveFromValueWithReferenceWrapper_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable( std::move(std::ref(mock_fooable)) );

    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}


TEST( TestVTableSBOCOWFooable, CopyAssignFromValue_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable;

    auto value = mock_fooable.foo();
    fooable = mock_fooable;
    test_interface(fooable, value, Mock::other_value);
}

TEST( TestVTableSBOCOWFooable, CopyAssignFromValue_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable;

    auto value = mock_fooable.foo();
    fooable = mock_fooable;
    test_interface(fooable, value, Mock::other_value);
}


TEST( TestVTableSBOCOWFooable, CopyAssignment_SmallObject )
{
    Fooable fooable = MockFooable();
    Fooable other;
    other = fooable;
    test_copies( other, fooable, Mock::other_value );
}

TEST( TestVTableSBOCOWFooable, CopyAssignment_LargeObject )
{
    Fooable fooable = MockLargeFooable();
    Fooable other;
    other = fooable;
    test_copies( other, fooable, Mock::other_value );
}


TEST( TestVTableSBOCOWFooable, CopyAssignFromValueWithReferenceWrapper_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable;

    fooable = std::ref(mock_fooable);
    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}

TEST( TestVTableSBOCOWFooable, CopyAssignFromValueWithReferenceWrapper_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable;

    fooable = std::ref(mock_fooable);
    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}


TEST( TestVTableSBOCOWFooable, MoveAssignFromValue_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable;

    auto value = mock_fooable.foo();
    fooable = std::move(mock_fooable);
    test_interface(fooable, value, Mock::other_value);
}

TEST( TestVTableSBOCOWFooable, MoveAssignFromValue_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable;

    auto value = mock_fooable.foo();
    fooable = std::move(mock_fooable);
    test_interface(fooable, value, Mock::other_value);
}


TEST( TestVTableSBOCOWFooable, MoveAssignment_SmallObject )
{
    Fooable fooable = MockFooable();
    auto value = fooable.foo();
    Fooable other;
    other = std::move(fooable);

    test_interface( other, value, Mock::other_value );
    death_tests(fooable);
}

TEST( TestVTableSBOCOWFooable, MoveAssignment_LargeObject )
{
    Fooable fooable = MockLargeFooable();
    auto value = fooable.foo();
    Fooable other;
    other = std::move(fooable);

    test_interface( other, value, Mock::other_value );
    death_tests(fooable);
}


TEST( TestVTableSBOCOWFooable, MoveAssignFromValueWithReferenceWrapper_SmallObject )
{
    MockFooable mock_fooable;
    Fooable fooable;

    fooable = std::move(std::ref(mock_fooable));
    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}

TEST( TestVTableSBOCOWFooable, MoveAssignFromValueWithReferenceWrapper_LargeObject )
{
    MockLargeFooable mock_fooable;
    Fooable fooable;

    fooable = std::move(std::ref(mock_fooable));
    test_ref_interface( fooable, mock_fooable, Mock::other_value );
}


TEST( TestVTableSBOCOWFooable, Cast_SmallObject )
{
    Fooable fooable = MockFooable();

//    EXPECT_TRUE( fooable.target<int>() == nullptr );
    ASSERT_FALSE( fooable.target<MockFooable>() == nullptr );

    fooable.set_value(Mock::other_value);
    EXPECT_EQ( fooable.target<MockFooable>()->foo(), Mock::other_value );
}

TEST( TestVTableSBOCOWFooable, Cast_LargeObject )
{
    Fooable fooable = MockLargeFooable();

//    EXPECT_TRUE( fooable.target<int>() == nullptr );
    ASSERT_FALSE( fooable.target<MockLargeFooable>() == nullptr );

    fooable.set_value(Mock::other_value);
    EXPECT_EQ( fooable.target<MockLargeFooable>()->foo(), Mock::other_value );
}


TEST( TestVTableSBOCOWFooable, ConstCast_SmallObject )
{
    const Fooable fooable = MockFooable();

//    EXPECT_TRUE( fooable.target<int>() == nullptr );
    ASSERT_FALSE( fooable.target<MockFooable>() == nullptr );

    EXPECT_EQ( fooable.target<MockFooable>()->foo(), Mock::value );
}

TEST( TestVTableSBOCOWFooable, ConstCast_LargeObject )
{
    const Fooable fooable = MockLargeFooable();

//    EXPECT_TRUE( fooable.target<int>() == nullptr );
    ASSERT_FALSE( fooable.target<MockLargeFooable>() == nullptr );

    EXPECT_EQ( fooable.target<MockLargeFooable>()->foo(), Mock::value );
}
