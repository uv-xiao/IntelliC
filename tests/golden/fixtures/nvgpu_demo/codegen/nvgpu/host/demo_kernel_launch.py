from htp.runtime import call_kernel, default_runtime

def launch_demo_kernel(*args, mode="sim", trace=None, runtime=None):
    resolved_runtime = default_runtime() if runtime is None else runtime
    return call_kernel(
        "demo_kernel.kernel0",
        args=args,
        mode=mode,
        trace=trace,
        runtime=resolved_runtime,
        artifacts={
            "backend": "nvgpu",
            "variant": "cuda",
            "hardware_profile": "nvidia:ampere:sm80",
            "kernel_source": "codegen/nvgpu/kernels/demo_kernel.cu",
        },
    )
