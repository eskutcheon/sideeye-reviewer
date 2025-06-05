
import functools
from dataclasses import dataclass, field
import io
import PIL.Image as PIL
import numpy as np
from typing import List, Dict, Any, Set, Callable, Protocol, runtime_checkable, Literal, Optional, Union
# importing RenderAsset for transforms decorators return type
from .etl_models import RenderAsset
from ..utils import transforms as t_utils


# TODO: move decoding functions to `utils/transforms.py` or `utils/utils.py` later
# TODO: also consider removing the less intuitive positional and keyword arguments like `*` or `**_`

def _decode_as_rgb(buf: bytes) -> np.ndarray:
    return np.array(PIL.open(io.BytesIO(buf)).convert("RGB"))

def img_decode_rgb(*, item_id: str, raw: bytes, ctx: dict, **_) -> RenderAsset:
    img = _decode_as_rgb(item_id=item_id, raw=raw, ctx=ctx, idx=0)
    return RenderAsset("image", img, target_axes=0)

def img_decode_rgb_list(*, item_id: str, raw: Union[bytes, List[bytes]], ctx: dict, **_) -> List[RenderAsset]:
    if isinstance(raw, bytes):
        # if raw is a single bytes object, decode it as a single image
        return [img_decode_rgb(item_id=item_id, raw=raw, ctx=ctx)]
    else:
        # if raw is a list of bytes objects, decode each as an image
        assets = []
        for i, buf in enumerate(raw):
            img = _decode_as_rgb(item_id=item_id, raw=buf, ctx=ctx, idx=i)
            assets.append(RenderAsset(kind="image", payload=img, target_axes=i))
        return assets


@runtime_checkable
class Transform(Protocol):
    def __call__(self, *, item_id: str, raw: Optional[bytes] = None,
                 img: Optional[Any] = None, ctx: Optional[dict] = None) -> Any: ...

class TransformContext(dict):
    """ Mutable (named) dictionary passed through the transform chain
        - can be used to store metadata, intermediate results, or configuration options
        - should be passed to each transform in the pipeline
    """


# ------------------------------------------------------------------
#  Transform utilities – functional objects with .requires/.produces
# ------------------------------------------------------------------

TransformFn = Callable[[Dict[str, Any], Dict[str, Any]],
                       Union[None, Dict[str, Any], RenderAsset, List[RenderAsset]]]

class TransformWrapper:
    """ Wrap a plain function and give it requires / produces sets
        Attach `.requires` / `.produces` metadata so the DAG engine can schedule plain functions
    """
    def __init__(self, fn: TransformFn, *, requires: List[str], produces: List[str]):
        self.fn = fn
        self.requires = list(requires)  # Store as list to preserve order
        self.produces = list(produces)  # Store as list to preserve order
        # for backward compatibility with set operations
        self._requires_set = set(requires)
        self._produces_set = set(produces)
        # copy dunder info for debuggability
        self.__name__ = fn.__name__
        self.__qualname__ = fn.__qualname__
        functools.update_wrapper(self, fn)

    def __call__(self, inputs: Dict[str, Any], ctx: Dict[str, Any]):
        return self.fn(inputs, ctx)






# ------------------------------------------------------------------
#  Figure template (bare‑bones)
# ------------------------------------------------------------------

# @dataclass
# class AxesTemplate:
#     slot: int                    # which subplot index
#     transform: str               # registry key below

# @dataclass
# class FigureTemplate:
#     axes: List[AxesTemplate]

#     @classmethod
#     def from_dict(cls, data: Dict[str, Any]):
#         return cls(axes=[AxesTemplate(**d) for d in data.get("axes", [])])

# -----------------------------------------------------------------
# minimal figure‑template glue  (reviewer/config.py idea)
# -----------------------------------------------------------------
# Given a parsed YAML list like [{'slot':0,'transform':'create_segmentation_mask_overlay'}, …]
# we can construct the PreLoaderModel pipeline as:
#
#   transforms = [TRANSFORM_REGISTRY[item['transform']] for item in template]
#   pre_loader  = PreLoaderModel(source, transforms)
#
# slot/axes assignment is embedded in each RenderAsset via wrapper logic.
# ==============================================================



# -------------------------- Transform  ---------------------------
# Every transform is a **callable** with metadata attributes
#  .requires : names it needs in the `inputs` dict
#  .produces : names it adds to the `inputs` dict
# It may return:
#   • None                     – only side‑effects on ctx/inputs
#   • Dict[str,Any]            – new keys to merge into inputs
#   • RenderAsset | List[RenderAsset]
#
# A lightweight decorator lets us tag ordinary functions:

# def transform(*, requires: Set[str] = frozenset(), produces: Set[str] = frozenset()):
#     def _wrap(fn):
#         fn.requires = set(requires)
#         fn.produces = set(produces)
#         return fn
#     return _wrap





# ---------------------------  thin wrappers  --------------------------------

TRANSFORM_REGISTRY: Dict[str, TransformWrapper] = {}

# def register(name: str, *, requires: set[str], produces: set[str]):
def register(name: str, *, requires: List[str] = None, produces: List[str] = None):
    """ Decorator to register a transform in the global map """
    if requires is None:
        requires = []
    if produces is None:
        produces = []
    # decorator function to wrap the transform function
    def _decorator(fn: TransformFn):
        TRANSFORM_REGISTRY[name] = TransformWrapper(fn, requires=requires, produces=produces)
        # mark template key for FigureTemplate lookup
        setattr(TRANSFORM_REGISTRY[name], "template_key", name)
        return fn
    return _decorator

#!!! FIXME: remove default target_axes in all assignments

#!!! FIXME: allow additional keyword arguments to the transform functions

# decode first buffer and expose as "img"
@register("decode_img", requires=["buf0"], produces=["img"])
def decode_img(inputs, ctx):
    """ buf0 -> img (no RenderAsset; lets later transforms decide what to do) """
    img = _decode_as_rgb(inputs["buf0"])
    return {"img": img}

@register("decode_mask", requires=["buf1"], produces=["mask"])
def decode_mask(inputs, ctx):
    mask = np.array(PIL.open(io.BytesIO(inputs["buf1"])).convert("L"))
    return {"mask": mask}

@register("seg_overlay", requires=["img", "mask"], produces=[])
def seg_overlay(inputs, ctx):
    overlay = t_utils.create_segmentation_mask_overlay(inputs["img"], inputs["mask"])
    return RenderAsset("image", overlay, target_axes=2)

@register("bbox_overlay", requires=["img", "bboxes"], produces=["bbox_img"])
def bbox_overlay(inputs, ctx):
    overlay = t_utils.create_bbox_overlay_pil(inputs["img"], inputs["bboxes"], colour=(0,255,0))
    return RenderAsset("image", overlay, target_axes=2)

@register("edge_mask", requires=["img"], produces=[])
def edge_mask(inputs, ctx):
    mask = t_utils.create_binary_edge_mask(inputs["img"], method="canny", adaptive_threshold=True).astype(bool)
    #mask = (255 * mask).astype(np.uint8) # ! TEMPORARY - just trying to see why it's defaulting to the wrong cmap
    print(f"Edge mask values: {np.unique(mask)}")
    return RenderAsset("image", mask, target_axes=2)

# @register("rgb_plot", requires={"img"}, produces=set())
# def rgb_plot(inputs, ctx):
#     def _plot(ax):
#         t_utils.create_rgb_distributions(inputs["img"], ax)
#     return RenderAsset("callable", _plot, target_axes=5)

@register("rgb_plot", requires=["img"], produces=[])
def rgb_plot(inputs, ctx):
    """ Return a callable that will draw on a viewer Axes later """
    plot_fn = lambda ax: t_utils.create_rgb_distributions()(inputs["img"], ax)  # returns inner populate_axes
    return RenderAsset("callable", plot_fn, target_axes=5)