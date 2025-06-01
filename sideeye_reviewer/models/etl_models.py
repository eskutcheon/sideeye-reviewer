

from dataclasses import dataclass, field
import io
import PIL.Image as PIL
import numpy as np
from typing import List, Dict, Any, Literal, Optional, Set, Iterable, Union, Callable



@dataclass
class RenderAsset:
    """ a container for plottable assets and render-plan that is explicit about where each asset belongs
        - gives the instructions for plotting an image or plot so that we're able to update a single axes or as
            many as all of them by returning a list of RenderAssets with the indices of the relevant axes
    """
    kind: Literal["image", "plot", "callable"]
    payload: Any #   # np.ndarray | mpl artist | plot object | Callable[[plt.Axes], None] to render
    target_axes: int # index into viewer.axes list #& 0‑based slot index in the viewer grid
    z_order: int = 0 # drawing order, higher means on top of lower z-order images (default for axes: patches, lines, text)


# @runtime_checkable
# class Transform(Protocol):
#     def __call__(self, *, item_id: str, raw: Optional[bytes] = None,
#                  img: Optional[Any] = None, ctx: Optional[dict] = None) -> Any: ...

# class TransformContext(dict):
#     """ Mutable (named) dictionary passed through the transform chain
#         - can be used to store metadata, intermediate results, or configuration options
#         - should be passed to each transform in the pipeline
#     """


@dataclass
class LoadResult:
    """ Container returned by PreLoaderModel after pre-loading pipeline runs - should be ready to pass to the viewer """
    item_id: str                # unique identifier (e.g., path relative to root)
    assets: List[RenderAsset]   # list of data to render combining primary and derived images, plots
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UpdateResult:
    """ Container returned by UpdaterModel (post-load augmentation) """
    assets: List[RenderAsset] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)



# TODO: add logic upstream to default to apply initial file reading and caching in the transforms list
# TODO: ensure that all transforms expect either a single raw bytes object or a list of bytes


class PreLoaderModel:
    """ Executes a DAG of transforms.  `transforms` may be:
       •  a list of TransformWrapper
       •  or strings looked-up in a global registry (see transforms.py)
    """
    def __init__(self, source, transforms: Iterable[Union[str, 'TransformWrapper']]): #, *, template: Optional[FigureTemplate] = None):
        # lazy imports to avoid cycles
        from .data_sources import DataSource
        from .aug_wrappers import TRANSFORM_REGISTRY, TransformWrapper #, FigureTemplate
        self.source: DataSource = source
        #self.template = template or FigureTemplate.from_dict({"axes": []})
        #! FIXME: this should probably become a list of lists of TransformWrapper
            # to separate the transforms for each axes' content (i.e. each image passed in `raw` in `self.load()`)
        self.transforms: List[TransformWrapper] = []
        self._separate_transforms = False
        for t in transforms:
            if isinstance(t, Iterable) and not isinstance(t, str):
                # if `transforms` is a nested iterable, assume it's a list of transforms for each axes
                self.transforms.append([])
                self._separate_transforms = True
                for tt in t:
                    if isinstance(tt, str):
                        self.transforms[-1].append(TRANSFORM_REGISTRY[tt])
                    else:
                        self.transforms[-1].append(tt)
            elif isinstance(t, str):
                self.transforms.append(TRANSFORM_REGISTRY[t])
            else:
                self.transforms.append(t)

    def _load_single(self, item_id: str, inputs: Dict[str, Any], transforms: List['TransformWrapper'], ctx: Dict[str, Any]) -> List[RenderAsset]:
        """ Apply a list of transforms to the given inputs using topological sorting
            Args:
                item_id: The identifier for the current item
                inputs: Dictionary of input data and intermediate products
                transforms: List of transforms to apply
                ctx: Context dictionary that may be modified by transforms
            Returns:
                List of RenderAsset objects produced by the transforms
        """
        produced: Set[str] = set(inputs.keys())
        remaining = transforms.copy()
        assets: List[RenderAsset] = []
        # Naive topological sort: loop until no progress or all transforms applied
        while remaining:
            progress = False
            for t in remaining[:]:
                if not t.requires.issubset(produced):
                    continue  # dependencies not ready yet
                print(f"[DEBUGGING] Executing transform {t.__name__}")
                print(f"[DEBUGGING] Transform {t.__name__} requires: {t.requires}, produced: {t.produces}")
                out = t(inputs, ctx)
                if isinstance(out, dict):
                    # update inputs with the dict returned by the transform
                    inputs.update(out)
                    produced.update(out.keys())
                elif isinstance(out, RenderAsset):
                    assets.append(out)
                elif isinstance(out, list):
                    assets.extend([a for a in out if isinstance(a, RenderAsset)])
                # mark current transform's products as produced
                produced.update(t.produces)
                remaining.remove(t)
                progress = True
            if not progress and remaining:
                missing = {t.__name__: t.requires - produced for t in remaining}
                raise RuntimeError(f"Unsatisfied transform dependencies: {missing}")
        return assets


    def load(self, item_id: str) -> LoadResult:
        raw: Union[bytes, bytearray, Iterable[bytes]] = self.source.load(item_id)
        #print("[DEBUGGING] raw type and length:", type(raw), len(raw) if isinstance(raw, (Iterable, bytearray)) else len(raw[0]) if raw else 0)
        # create shared context dictionary
        ctx: Dict[str, Any] = {}
        all_assets: List[RenderAsset] = []
        if self._separate_transforms:
            # handle case where transforms is a list of lists
            if isinstance(raw, (bytes, bytearray)):
                # single raw buffer but multiple transform chains - use first transform chain
                inputs = {"buf0": raw}
                assets = self._load_single(item_id, inputs, self.transforms[0], ctx)
                all_assets.extend(assets)
            else:
                # multiple raw buffers, apply corresponding transform chains
                for i, buf in enumerate(raw):
                    if i < len(self.transforms):  # Only process if we have transforms for this buffer
                        inputs = {f"buf{i}": buf}
                        assets = self._load_single(item_id, inputs, self.transforms[i], ctx) 
                        all_assets.extend(assets)
        else:
            # single list of transforms for all inputs
            inputs: Dict[str, Any] = {}
            if isinstance(raw, (bytes, bytearray)):
                inputs["buf0"] = raw
            else:  # list[bytes]
                for i, buf in enumerate(raw):
                    inputs[f"buf{i}"] = buf
            all_assets = self._load_single(item_id, inputs, self.transforms, ctx)
        # fallback if no assets were produced
        if not all_assets:
            if "img" in ctx and isinstance(ctx["img"], np.ndarray):
                all_assets.append(RenderAsset("image", ctx["img"], target_axes=0))
            else:
                # decode every raw buf as an image
                bufs = raw if isinstance(raw, Iterable) and not isinstance(raw, (bytes, bytearray)) else [raw]
                for i, buf in enumerate(bufs):
                    img = np.array(PIL.open(io.BytesIO(buf)).convert("RGB"))
                    all_assets.append(RenderAsset("image", img, target_axes=i))
        #print("[DEBUGGING] final assets:", [f"{a.kind} on axes {a.target_axes}" for a in all_assets])
        #print("[DEBUGGING] final ctx:", ctx)
        return LoadResult(item_id=item_id, assets=all_assets, metadata=ctx)


class PostLoaderModel:
    """ Runs post-load transforms in response to a GUI event initiated by the user
        (e.g., button toggle for applying an image augmentation or generating a plot)
        - to be used to update the displayed image or add new plots
    """
    from .aug_wrappers import Transform
    def __init__(self, transforms: List[Transform]):
        self.transforms = transforms

    # def apply(self, item_ctx: LoadResult, user_event: Dict[str, Any]) -> UpdateResult:
    #     ctx = dict(item_ctx.metadata) or {"event": user_event}
    #     updated_assets: List[RenderAsset] = []
    #     for t in self.transforms:
    #         result = t(item_id=item_ctx.item_id, img=None, ctx=ctx)
    #         if isinstance(result, RenderAsset):
    #             updated_assets.append(result)
    #         elif isinstance(result, list):
    #             updated_assets.extend([a for a in result if isinstance(a, RenderAsset)])
    #     return UpdateResult(assets=updated_assets, metadata=ctx)

    def apply(self, lr: LoadResult, user_event: Dict[str, Any]) -> UpdateResult:
        """ apply post-load transforms to the loaded assets / user event """
        inputs = {**lr.metadata, **user_event}
        ctx: Dict[str, Any] = {}
        assets: List[RenderAsset] = []
        for t in self.transforms:
            out = t(inputs=inputs, ctx=ctx)
            if isinstance(out, RenderAsset):
                assets.append(out)
            elif isinstance(out, list):
                assets.extend(out)
        return UpdateResult(assets=assets, metadata=ctx)