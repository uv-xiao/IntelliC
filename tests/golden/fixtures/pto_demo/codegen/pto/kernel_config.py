KERNELS = [{"func_id": 0, "source": "kernels/aiv/demo_kernel.cpp", "core_type": "aiv"}]
ORCHESTRATION = {
    "source": "orchestration/demo_kernel_orchestration.cpp",
    "function_name": "demo_kernel_orchestrate",
}
RUNTIME_CONFIG = {"runtime": "host_build_graph", "platform": "a2a3sim", "aicpu_thread_num": 1, "block_dim": 1}
