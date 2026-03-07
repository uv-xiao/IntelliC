STAGE_ID = "s01"


def run(*args, **kwargs):
    return {"backend": "nvgpu", "entry": "demo_kernel", "profile": "nvidia:ampere:sm80"}
