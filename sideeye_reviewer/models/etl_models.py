

from dataclasses import dataclass, field
import io
import PIL.Image as PIL
import numpy as np
from typing import List, Dict, Any, Tuple, Protocol, runtime_checkable, Literal, Optional




@dataclass
class RenderAsset:  #& NEW
    """ a container for plottable assets and render-plan that is explicit about where each asset belongs
        - gives the instructions for plotting an image or plot so that we're able to update a single axes or as
            many as all of them by returning a list of RenderAssets with the indices of the relevant axes
    """
    kind: Literal["image", "plot"]
    payload: Any #   #& UPDATED: numpy array, plot object, etc to render
    target_axes: int # index into viewer.axes list
    z_order: int = 0 # drawing order, higher means on top of lower z-order images (default for axes: patches, lines, text)


@runtime_checkable
class Transform(Protocol):
    def __call__(self, *, item_id: str, raw: Optional[bytes] = None,
                 img: Optional[Any] = None, ctx: Optional[dict] = None) -> Any: ...

class TransformContext(dict):
    """ Mutable (named) dictionary passed through the transform chain
        - can be used to store metadata, intermediate results, or configuration options
        - should be passed to each transform in the pipeline
    """


@dataclass
class LoadResult:
    """ Container returned by PreLoaderModel after pre-loading pipeline runs - should be ready to pass to the viewer """
    item_id: str                    # unique identifier (e.g., path relative to root)
    assets: List[RenderAsset] #& UPDATED: list of data to render combining primary and derived images, plots
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UpdateResult:
    """ Container returned by UpdaterModel (post-load augmentation) """
    assets: List[RenderAsset] = field(default_factory=list)  #& UPDATED: list of data to render combining primary and derived images, plots
    metadata: Dict[str, Any] = field(default_factory=dict)



class PreLoaderModel:
    """ Runs pre-load transform pipeline once per item_id - does disk I/O and prepares data for rendering """
    def __init__(self, source, transforms: Optional[List[Transform]] = None):
        from .data_sources import DataSource  # local import to avoid circulars
        self.source: DataSource = source
        # TODO: add logic upstream to default to initial file reading and caching in the transforms list
        self.load_transforms = transforms or []

    def _decode_list_fallback(self, raw_list: List[bytes]) -> List[RenderAsset]:
        assets: List[RenderAsset] = []
        for i, buf in enumerate(raw_list):
            img = np.array(PIL.open(io.BytesIO(buf)).convert("RGB"))
            assets.append(RenderAsset(kind="image", payload=img, target_axes=i))
        return assets

    # main load method that runs the pre-load transforms
    def load(self, item_id: str) -> LoadResult:
        raw = self.source.load(item_id)
        ctx: TransformContext = TransformContext(item_id=item_id)
        assets: List[RenderAsset] = [] #& UPDATED: list of data to render combining primary and derived images, plots
        # every transform now yields either a RenderAsset or modifies ctx
        for t in self.load_transforms:
            #! PROBABLY ABOUT TO CAUSE ISSUES: expects a single raw bytes object, not a list of bytes
            out = t(item_id=item_id, raw=raw, ctx=ctx)
            if isinstance(out, RenderAsset):
                assets.append(out)
            # TODO: might want to make the fallback used after the loop into the primary approach
            elif isinstance(out, list):
                assets.extend([a for a in out if isinstance(a, RenderAsset)])
        # automatic fallback if no assets were created by the transforms
        if not assets:
            print("[PRELOADER] No assets created by transforms, using fallback decoding.")
            if isinstance(raw, list):
                assets = self._decode_list_fallback(raw)
            else:
                # single buffer → axis 0
                assets = self._decode_list_fallback([raw])
        return LoadResult(item_id=item_id, assets=assets, metadata=ctx) #primary_img=img, derived=derived,


class PostLoaderModel:
    """ Runs post-load transforms in response to a GUI event initiated by the user
        (e.g., button toggle for applying an image augmentation or generating a plot)
        - to be used to update the displayed image or add new plots
    """
    def __init__(self, transforms: List[Transform]):
        self.transforms = transforms

    def apply(self, item_ctx: LoadResult, user_event: Dict[str, Any]) -> UpdateResult:
        ctx = dict(item_ctx.metadata) or {"event": user_event}
        updated_assets: List[RenderAsset] = []
        for t in self.transforms:
            result = t(item_id=item_ctx.item_id, img=None, ctx=ctx)
            if isinstance(result, RenderAsset):
                updated_assets.append(result)
            elif isinstance(result, list):
                updated_assets.extend([a for a in result if isinstance(a, RenderAsset)])
        return UpdateResult(assets=updated_assets, metadata=ctx)    #& OLD: redraw_images=redraw, extra_plots=extra,