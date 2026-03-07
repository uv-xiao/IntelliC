#include <cstdint>

#ifndef __gm__
#define __gm__
#endif

#ifndef __aicore__
#define __aicore__
#endif

// PTO simulation kernels are loaded with dlopen+dlsym("kernel_entry").
extern "C" __aicore__ __attribute__((always_inline)) void kernel_entry(__gm__ int64_t* args) {
    (void)args;
}
