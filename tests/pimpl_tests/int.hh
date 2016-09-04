#pragma once

namespace Pimpl
{
struct Int
{
    Int(int val) : value(val) { }

    operator int( ) { return value; }

    int value;
};

inline bool operator==(int a, Int b) { return a == b.value; }

inline bool operator==(Int a, int b) { return a.value == b; }
}
