#include <gtest/gtest.h>

#define TYPE_ERASURE_BUFFER_SIZE 100

int main(int argc, char **argv) {
    ::testing::InitGoogleTest( &argc, argv );
    return RUN_ALL_TESTS();
}
