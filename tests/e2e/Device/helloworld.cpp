// Device-side test target. greet() exists so the DAP probe has a symbol to
// break on; the loop gives it 5 hits.
#include <cstdio>

void greet(int i) {
    printf("hello %d\n", i);
}

int main() {
    printf("hello world\n");
    for (int i = 0; i < 5; ++i) {
        greet(i);
    }
    printf("bye\n");
    return 0;
}
