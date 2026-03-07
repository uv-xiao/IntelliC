#include <cuda_runtime.h>

extern "C" __global__ void demo_kernel_kernel0() {
  // profile: ampere
  (void)threadIdx.x;
}
