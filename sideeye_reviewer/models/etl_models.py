

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

    #~ IDEA: might actually add transformations directly to the dataclass to create derived assets easily

@dataclass
class UpdateResult:
    """ Container returned by UpdaterModel (post-load augmentation) """
    assets: List[RenderAsset] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)



# TODO: add logic upstream to default to apply initial file reading and caching in the transforms list

from .aug_wrappers import TRANSFORM_REGISTRY, TransformWrapper

class PreLoaderModel:
    """ Executes a DAG of transforms.  `transforms` may be:
       •  a list of TransformWrapper
       •  or strings looked-up in a global registry (see transforms.py)
    """
    #! FIXME: might remove the transforms from the constructor, encapsulate it within `LoadResult`, and attach transforms before calling to `load()`
        #~ currently, the earlier stage is in the `DataManager`, which only passes `item_id` and no transforms
        #~ if we integrate the `FigureTemplate`, I might make something like `SlotData` to act as a builder much like `AxesData` or `FigureData`
    def __init__(self, source, transforms: Iterable[Union[str, 'TransformWrapper']] = None): #, *, template: Optional[FigureTemplate] = None):
        # lazy imports to avoid cycles
        from .data_sources import DataSource
        #from .aug_wrappers import TRANSFORM_REGISTRY, TransformWrapper #, FigureTemplate
        self.source: DataSource = source
        #self.template = template or FigureTemplate.from_dict({"axes": []})
        self.transforms: List[TransformWrapper] = []
        self._separate_transforms = False
        self._init_transforms(transforms)  # initialize transforms from the provided list or default to decoding images

    def get_num_to_plot(self) -> int:
        """ Returns the number of axes to plot based on the transforms, template, or number loaded by the source each time """
        if self._separate_transforms:
            return len(self.transforms)
        try:
            return self.source.num_roots
        except AttributeError:
            raise AttributeError("Current DataSource does not provide num_roots and/or transforms are not separated per axis.")

    def _init_transforms(self, transforms: Iterable[Union[str, 'TransformWrapper']] = None):
        """ Initialize transforms from a list of strings or TransformWrapper objects """
        if not transforms:
            transforms = ["decode_img"]  # default to decoding images if no transforms provided
        for t in transforms:
            if isinstance(t, Iterable) and not isinstance(t, str):
                # if `transforms` is a nested iterable, assume it's a list of transforms for each axes
                self._separate_transforms = True
                self.transforms.append([self._validate_transform(tt) for tt in t])
            else:
                self.transforms.append(self._validate_transform(t))

    def _validate_transform(self, transform: Union[str, 'TransformWrapper']):
        """ Add a single transform to the list, converting string names to TransformWrapper if needed """
        if isinstance(transform, str):
            try:
                return TRANSFORM_REGISTRY[transform]
            except KeyError:
                raise ValueError(f"Transform '{transform}' with type {type(transform)} not found in transforms registry.")
        elif isinstance(transform, TransformWrapper):
            return transform
        elif callable(transform):
            return TransformWrapper(transform)
        else:
            raise TypeError(f"Unsupported transform type: {type(transform)}. Expected str, TransformWrapper, or callable.")

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
                if not t._requires_set.issubset(produced): # use the set version of requires for subset check
                    continue  # dependencies not ready yet
                # print(f"[DEBUGGING] Executing transform {t.__name__}")
                # print(f"[DEBUGGING] Transform {t.__name__} requires: {t.requires}, produced: {t.produces}")
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
                produced.update(t._produces_set)  # use the set version of produces for updates
                remaining.remove(t)
                progress = True
            if not progress and remaining:
                missing = {t.__name__: t._requires_set - produced for t in remaining}
                raise RuntimeError(f"Unsatisfied transform dependencies: {missing}")
        return assets


    # TODO: [x] add a simple temporary measure that, in the case where the number of independent transforms > len(raw),
        # infers inputs to later transforms as the first n elements of the raw buffer based on num arguments of the transform

    def load(self, item_id: str) -> LoadResult:
        """ Load data for the given item_id, apply transforms, and return LoadResult."""
        raw: Union[bytes, bytearray, Iterable[bytes]] = self.source.load(item_id)
        num_raw_assets = 1 if isinstance(raw, (bytes, bytearray)) else len(raw)
        #~ Split orchestration logic further here -
        #print("[DEBUGGING] raw type and length:", type(raw), len(raw) if isinstance(raw, (Iterable, bytearray)) else len(raw[0]) if raw else 0)
        # TODO: might want to incorporate the context dictionaries into the LoadResult directly
        # create shared context dictionary
        ctx: Dict[str, Any] = {}
        all_assets: List[RenderAsset] = []
        #! FIXME: basically all of this needs to be replaced with something more robust without reliance on input argument names
            #~ general idea I had is creating custom wrappers for each type of input data and determine treatment based on that
                #~ e.g. "ImagePayload" for bytes that are expected to be decoded as images, "MaskPayload" for masks,
                #~ DerivedPayload for derived assets that has a description of input types (other payload classes)
                #~ the latter wouldn't wrap bytes but the final payload type, however - may or may not be a callable
                #~ this may also be good for handling non-image input that's needed for some transforms, like bounding box indices
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
        if self._separate_transforms and len(self.transforms) > num_raw_assets:
            print("[DEBUGGING] Applying remaining transforms to derived assets...")
            # if we have more transforms than raw buffers, assume remaining transforms produce derived assets
            for idx, t in enumerate(self.transforms[num_raw_assets:]):
                try:
                    # TODO: need to figure out an approach for non-image data like the bounding box indices too
                    for tt in t:
                        #! PROBLEM: the `TransformWrapper.requires` is a set, which doesn't preserve order; We can't reliably map the first to always
                            #! be the image buffer and second to be the mask either since the order in the source only depends on the original input order
                        inputs = {arg: np.array(PIL.open(io.BytesIO(raw[i])).convert("RGB")) for i, arg in enumerate(tt.requires)}
                        assets: List[RenderAsset] = self._load_single(item_id, inputs, [tt], ctx)
                        assets[0].target_axes = num_raw_assets + idx  #! TEMPORARY PATCH: base RenderAsset's target_axes on the current index in the transforms list
                        all_assets.extend(assets)
                        #!!! think the issue with the inconsistency in the order of the buffer and the returned transforms is the way `ctx` is handled
                except Exception as e:
                    print(f"[DEBUGGING] Error applying remaining transforms: {e}")
                    pass
        return LoadResult(item_id=item_id, assets=all_assets, metadata=ctx)


class PostLoaderModel:
    """ Runs post-load transforms in response to a GUI event initiated by the user
        (e.g., button toggle for applying an image augmentation or generating a plot)
        - to be used to update the displayed image or add new plots
    """
    from .aug_wrappers import Transform
    def __init__(self, transforms: List[Transform]):
        self.transforms = transforms


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