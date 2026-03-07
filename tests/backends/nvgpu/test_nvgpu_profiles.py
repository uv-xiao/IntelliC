from htp.backends.nvgpu.arch import arch_for


def test_ampere_and_blackwell_are_profiles_of_one_backend():
    ampere = arch_for("ampere")
    blackwell = arch_for("blackwell")

    assert ampere.backend == "nvgpu"
    assert blackwell.backend == "nvgpu"
    assert ampere.variant == "cuda"
    assert blackwell.variant == "cuda"
    assert ampere.hardware_profile == "nvidia:ampere:sm80"
    assert blackwell.hardware_profile == "nvidia:blackwell:sm100"
    assert ampere.memory_spaces == ("global", "shared", "register")
    assert blackwell.memory_spaces == ("global", "shared", "register")
    assert ampere.cuda_arches == ("sm80",)
    assert blackwell.cuda_arches == ("sm100",)
    assert ampere.capabilities == ("cp.async", "mma.sync")
    assert blackwell.capabilities == ("cp.async.bulk", "tma", "wgmma")
