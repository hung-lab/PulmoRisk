# lung.spec
# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

# ── Collect packages ───────────────────────────────────────────────────────────
ctk_datas,    ctk_binaries,    ctk_hidden    = collect_all("customtkinter")
sybil_datas,  sybil_binaries,  sybil_hidden  = collect_all("sybil")
torch_datas,  torch_binaries,  torch_hidden  = collect_all("torch")
tv_datas,     tv_binaries,     tv_hidden     = collect_all("torchvision")
pil_datas,    pil_binaries,    pil_hidden    = collect_all("PIL")


# ── Static assets ──────────────────────────────────────────────────────────────
datas = (
    ctk_datas
    + sybil_datas
    + torch_datas
    + tv_datas
    + pil_datas
)

if os.path.exists("src/app/assets"):
    datas += [("src/app/assets", "assets")]

if os.path.exists("app_icon.png"):
    datas += [("app_icon.png", ".")]

# ── Binaries ───────────────────────────────────────────────────────────────────
binaries = (
    ctk_binaries
    + sybil_binaries
    + torch_binaries
    + tv_binaries
    + pil_binaries
)

# ── Hidden imports ─────────────────────────────────────────────────────────────
hiddenimports = (
    ctk_hidden
    + sybil_hidden
    + torch_hidden
    + tv_hidden
    + pil_hidden
    + [
        # PIL
        "PIL.ImageTk",
        "PIL._tkinter_finder",
        # multiprocessing spawn — required for worker process in frozen app
        "multiprocessing",
        "multiprocessing.spawn",
        "multiprocessing.forkserver",
        "multiprocessing.popen_spawn_posix",
        "multiprocessing.popen_fork",
        "multiprocessing.process",
        "multiprocessing.queues",
        "multiprocessing.reduction",
        "multiprocessing.synchronize",
        "multiprocessing.resource_tracker",
        # worker module must be explicitly included so the spawned
        # child process can import it from the frozen bundle
        "app.utils.sybil_worker",
        "app.models.patient_model",
        "app.utils.sybil_epi",
    ]
)

# ── Excludes — remove dead torch code to shrink bundle ────────────────────────
excludes = [
    # torch subsystems — safe to exclude for sybil inference
    "torch.distributed",
    "torch.distributed.rpc",
    "torch.distributed.optim",
    "torch.utils.tensorboard",
    "torch.utils.bottleneck",
    "torch.onnx",
    "torch.export",
    "torch.profiler",
    # testing / dev tools
    "pytest",
    "xmlrunner",
    "hypothesis",
    # notebook / IPython
    "IPython",
    "ipykernel",
    "jupyter",
    "notebook",
]

# ── Analysis ───────────────────────────────────────────────────────────────────
a = Analysis(
    ["src/app/main.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# ── Executable ────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="pulmorisk",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,   # stripping torch .so files can break CUDA — leave False
    upx=False,     # UPX corrupts torch/CUDA libs — never enable
    console=False,
    icon="app_icon.png" if os.path.exists("app_icon.png") else None,
)

# ── One-dir collect ───────────────────────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="PulmoRisk",
)
