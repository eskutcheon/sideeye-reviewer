# ==============================================================
#  Image‑Annotation Reviewer – DAG‑based Transform Pipeline & Template
#  -------------------------------------------------------------------
#  This scaffold shows all **new / changed code** required for:
#    •  Issue #2: swap the flat transform list for a small DAG
#    •  Issue #3: minimal Figure‑template → pipeline glue
#    •  Issue #6: pure numpy/PIL helpers + thin wrappers registered as
#       DAG transforms.
# -------------------------------------------------------------------
#  Copy each section into the real project modules (`etl_models.py`,
#  `transforms.py`, etc.).  Everything continues to compile standalone…
# ==============================================================

"""etl_models.py ­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any, Set, Iterable, Optional, Union, Literal
import networkx as nx  # lightweight, pure‑py topo sort

# ------------------------------------------------------------------
#  RenderAsset (unchanged ‑ just add optional callable kind)
# ------------------------------------------------------------------

@dataclass
class RenderAsset:
    kind: Literal["image", "plot", "callable"]
    payload: Any
    target_axes: int
    z_order: int = 0

@dataclass
class LoadResult:
    item_id: str
    assets: List[RenderAsset]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UpdateResult:
    assets: List[RenderAsset]
    metadata: Dict[str, Any] = field(default_factory=dict)

# ------------------------------------------------------------------
#  Transform utilities – functional objects with .requires/.produces
# ------------------------------------------------------------------

TransformFn = Callable[[Dict[str, Any], Dict[str, Any]], Union[None, Dict[str, Any], RenderAsset, List[RenderAsset]]]

class TransformWrapper:
    """Wrap a plain function and give it requires / produces sets."""
    def __init__(self, fn: TransformFn, *, requires: Set[str], produces: Set[str]):
        self.fn = fn
        self.requires = set(requires)
        self.produces = set(produces)
        # copy dunder info for debuggability
        self.__name__ = fn.__name__
        self.__qualname__ = fn.__qualname__

    def __call__(self, inputs: Dict[str, Any], ctx: Dict[str, Any]):
        return self.fn(inputs, ctx)

# ------------------------------------------------------------------
#  Figure template (bare‑bones)
# ------------------------------------------------------------------

@dataclass
class AxesTemplate:
    slot: int                    # which subplot index
    transform: str               # registry key below

@dataclass
class FigureTemplate:
    axes: List[AxesTemplate]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(axes=[AxesTemplate(**d) for d in data.get("axes", [])])

# ------------------------------------------------------------------
#  PreLoaderModel with DAG execution
# ------------------------------------------------------------------

class PreLoaderModel:
    """Executes a DAG of transforms.  `transforms` may be:
       •  a list of TransformWrapper
       •  or strings looked‑up in a global registry (see transforms.py)
    """

    def __init__(self, source, transforms: Iterable[Union[str, TransformWrapper]], *, template: Optional[FigureTemplate] = None):
        from .transforms import TRANSFORM_REGISTRY  # local import to avoid cycle
        self.source = source
        self.template = template or FigureTemplate.from_dict({"axes": []})
        self.transforms: List[TransformWrapper] = []
        for t in transforms:
            if isinstance(t, str):
                self.transforms.append(TRANSFORM_REGISTRY[t])
            else:
                self.transforms.append(t)

    # ----------------------------
    def load(self, item_id: str) -> LoadResult:
        raw = self.source.load(item_id)  # bytes *or* list[bytes]

        # 1. build initial input dict ---------------------------------
        inputs: Dict[str, Any] = {}
        if isinstance(raw, bytes):
            inputs["buf0"] = raw
        else:  # list[bytes]
            for i, buf in enumerate(raw):
                inputs[f"buf{i}"] = buf
        ctx: Dict[str, Any] = {}

        # 2. topo‑execute transforms ---------------------------------
        assets: List[RenderAsset] = []
        remaining = list(self.transforms)
        produced: Set[str] = set(inputs.keys())

        # naïve topo sort (loop until no progress); raise if cycle
        while remaining:
            progress = False
            for t in remaining[:]:
                if t.requires.issubset(produced):
                    out = t(inputs, ctx)
                    if out is None:
                        pass
                    elif isinstance(out, RenderAsset):
                        assets.append(out)
                    elif isinstance(out, list):
                        assets.extend(out)
                    elif isinstance(out, dict):
                        inputs.update(out)
                        produced.update(out.keys())
                    else:
                        raise TypeError(f"Unexpected transform output from {t}: {type(out)}")
                    produced.update(t.produces)
                    remaining.remove(t)
                    progress = True
            if not progress:
                raise RuntimeError("Transform dependency cycle or unsatisfied inputs")

        # 3. If a template is present, enforce axes assignment --------
        if self.template.axes:
            for ax_t in self.template.axes:
                # find first asset whose function matches template key
                for a in assets:
                    if getattr(a, "template_key", None) == ax_t.transform:
                        a.target_axes = ax_t.slot
                        break

        return LoadResult(item_id=item_id, assets=assets, metadata=ctx)

# PostLoaderModel unchanged for brevity --------------------------------------

"""transforms.py ­­­ pure helpers + registry ­­­"""
from __future__ import annotations
import numpy as np
import cv2
from PIL import Image, ImageDraw
from skimage.metrics import structural_similarity as ssim
import matplotlib.pyplot as plt
from typing import Dict, Any, List
from .etl_models import RenderAsset, TransformWrapper

# ---------------------------  pure numpy/PIL funcs --------------------------

def _blend(img: np.ndarray, mask_rgb: np.ndarray, alpha: float) -> np.ndarray:
    return (img * (1 - alpha) + mask_rgb * alpha).astype(img.dtype)

# 1. segmentation mask overlay ----------------------------------------------

def create_segmentation_mask_overlay(img: np.ndarray, mask: np.ndarray, *, alpha: float = 0.5) -> np.ndarray:
    # assume mask is H×W with class IDs.  Map to colours deterministically.
    palette = np.array([
        [0, 0, 0], [128, 0, 0], [0, 128, 0], [0, 0, 128],
        [128, 128, 0], [128, 0, 128], [0, 128, 128], [128, 128, 128]
    ], dtype=np.uint8)
    mask_rgb = palette[mask % len(palette)]
    return _blend(img, mask_rgb, alpha)

# 2. bounding box overlay ----------------------------------------------------

def create_bbox_overlay_pil(img: np.ndarray, bboxes: np.ndarray, *, colour=(255, 0, 0), width: int = 2) -> np.ndarray:
    pil = Image.fromarray(img)
    draw = ImageDraw.Draw(pil)
    for x1, y1, x2, y2 in bboxes.astype(int):
        draw.rectangle([x1, y1, x2, y2], outline=colour, width=width)
    return np.array(pil)

# 3. binary edge mask --------------------------------------------------------

def create_binary_edge_mask(img_gray: np.ndarray, *, thresh1=100, thresh2=200) -> np.ndarray:
    edges = cv2.Canny(img_gray, thresh1, thresh2)
    return edges > 0

# 4. morphological gradient mask --------------------------------------------

def create_morphological_gradient_mask(mask: np.ndarray, *, ksize: int = 3) -> np.ndarray:
    kernel = np.ones((ksize, ksize), np.uint8)
    grad = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_GRADIENT, kernel)
    return grad > 0

# 5. SSIM heatmap ------------------------------------------------------------

def create_ssim_heatmap(img1: np.ndarray, img2: np.ndarray) -> np.ndarray:
    ssim_val, heat = ssim(img1, img2, channel_axis=-1, full=True)
    # normalise 0‑1 to 0‑255 jet for display
    heat = (heat * 255).astype(np.uint8)
    heat_color = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
    return heat_color

# 6. RGB distributions plot --------------------------------------------------

def create_rgb_distributions(img: np.ndarray, ax: plt.Axes):
    channels = ("R", "G", "B")
    for i, c in enumerate(channels):
        ax.hist(img[..., i].ravel(), bins=256, histtype="step", label=c)
    ax.set_title("RGB hist")
    ax.legend()

# ---------------------------  thin wrappers  --------------------------------

TRANSFORM_REGISTRY: Dict[str, TransformWrapper] = {}

def register(name: str, *, requires: set[str], produces: set[str]):
    def _decor(fn):
        TRANSFORM_REGISTRY[name] = TransformWrapper(fn, requires=requires, produces=produces)
        # mark template key for FigureTemplate lookup
        setattr(TRANSFORM_REGISTRY[name], "template_key", name)
        return fn
    return _decor

# decode first buffer and expose as "img"
@register("decode_img", requires={"buf0"}, produces={"img"})
def _(inputs, ctx):
    import io
    img = np.array(Image.open(io.BytesIO(inputs["buf0"])).convert("RGB"))
    return {"img": img}

@register("decode_mask", requires={"buf1"}, produces={"mask"})
def _(inputs, ctx):
    import io
    mask = np.array(Image.open(io.BytesIO(inputs["buf1"]).convert("L")))
    return {"mask": mask}

@register("seg_overlay", requires={"img", "mask"}, produces={"overlay"})
def _(inputs, ctx):
    overlay = create_segmentation_mask_overlay(inputs["img"], inputs["mask"], alpha=0.4)
    return RenderAsset("image", overlay, target_axes=1)

@register("bbox_overlay", requires={"img", "bboxes"}, produces={"bbox_img"})
def _(inputs, ctx):
    overlay = create_bbox_overlay_pil(inputs["img"], inputs["bboxes"], colour=(0,255,0))
    return RenderAsset("image", overlay, target_axes=2)

@register("rgb_plot", requires={"img"}, produces=set())
def _(inputs, ctx):
    def _plot(ax):
        create_rgb_distributions(inputs["img"], ax)
    return RenderAsset("callable", _plot, target_axes=5)

# ---------------------------------------------------------------------------
#  Figure‑template example (user YAML → dict → FigureTemplate)
# ---------------------------------------------------------------------------
DEFAULT_TEMPLATE = FigureTemplate.from_dict({
    "axes": [
        {"slot": 0, "transform": "decode_img"},
        {"slot": 1, "transform": "seg_overlay"},
        {"slot": 5, "transform": "rgb_plot"}
    ]
})
