# lung-mac.spec
import os
import certifi
from PyInstaller.utils.hooks import collect_all

ctk_datas,   ctk_binaries,   ctk_hidden   = collect_all("customtkinter")
sybil_datas, sybil_binaries, sybil_hidden = collect_all("sybil")
torch_datas, torch_binaries, torch_hidden = collect_all("torch")
tv_datas,    tv_binaries,    tv_hidden    = collect_all("torchvision")
pil_datas,   pil_binaries,   pil_hidden   = collect_all("PIL")

datas = ctk_datas + sybil_datas + torch_datas + tv_datas + pil_datas
if os.path.exists("src/app/assets"):
    datas += [("src/app/assets", "assets")]
if os.path.exists("src/app/assets/icons/app_icon.icns"):
    datas += [("src/app/assets/icons", "assets/icons")]

datas += [
    (certifi.where(), "certifi"),
]

binaries = ctk_binaries + sybil_binaries + torch_binaries + tv_binaries + pil_binaries

hiddenimports = (
    ctk_hidden + sybil_hidden + torch_hidden + tv_hidden + pil_hidden
    + [
        "PIL.ImageTk",
        "PIL._tkinter_finder",
        "app.utils.sybil_worker",
        "app.models.individual_model",
        "app.utils.sybil_epi",
    ]
)

excludes = [
    "torch.distributed", "torch.distributed.rpc", "torch.distributed.optim",
    "torch.utils.tensorboard", "torch.utils.bottleneck",
    "torch.onnx", "torch.export", "torch.profiler",
    "pytest", "xmlrunner", "hypothesis",
    "IPython", "ipykernel", "jupyter", "notebook",
]

a = Analysis(
    ["src/app/main.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="pulmorisk",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon="src/app/assets/icons/app_icon.icns",
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, name="pulmorisk",
)

version = os.environ.get("VERSION", "0.0.0")

app = BUNDLE(
    coll,
    name="PulmoRisk.app",
    icon="src/app/assets/icons/app_icon.icns",
    bundle_identifier="ca.hung-lab.pulmorisk",
    info_plist={
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "NSHumanReadableCopyright": f"Copyright © 2026",
    },
)
