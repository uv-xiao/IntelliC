#include "runtime.h"
#include <cstdint>
#include <iostream>

// PTO host_build_graph orchestration ABI expected by pto-runtime:
//   extern "C" int entry(Runtime*, uint64_t*, int)
// The v1 package emits a minimal smoke task so HTP can prove the
// real a2a3sim execution path before richer tensor marshaling lands.
extern "C" int demo_kernel_orchestrate(Runtime* runtime, uint64_t* args, int arg_count) {
    (void)args;
    (void)arg_count;
    if (runtime == nullptr) {
        std::cerr << "orchestration received null runtime" << '\n';
        return -1;
    }
    const int task0 = runtime->add_task(nullptr, 0, 0, CoreType::AIV);
    if (task0 < 0) {
        std::cerr << "failed to add PTO smoke task" << '\n';
        return -1;
    }
    runtime->print_runtime();
    return 0;
}
