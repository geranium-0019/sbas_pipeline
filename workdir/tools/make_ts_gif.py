#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Make an animated GIF of cumulative displacement from a MintPy timeseries file.

- Reference day can be the first acquisition (default) or a specific date.
- Fixed or robust vlim (min/max) selection.
- Diverging colormap (default: RdBu_r) with 0-centered TwoSlopeNorm when vlim symmetric.

Dependencies: mintpy, matplotlib, imageio, numpy
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")  # safe for headless
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import imageio.v2 as imageio

from mintpy.objects import timeseries as TsObj
from mintpy.utils import readfile, plot as pp, utils as ut, ptime


def make_cumdisp_gif(
    ts_file: str,
    out_gif: str,
    *,
    mask_file: str | None = None,
    disp_unit: str = "cm",
    vlim: tuple[float, float] | None = (-30.0, 30.0),
    vlim_percentile: tuple[float, float] | None = None,  # e.g. (2, 98)
    cmap_name: str = "RdBu_r",
    fps: int = 5,
    ref: str = "first",           # "first" or "date"
    ref_date: str | None = None,  # "YYYYMMDD" when ref=="date"
    start_date: str | None = None,  # "YYYYMMDD": ignore dates before this
    wrap: bool = False,
    wrap_range: tuple[float, float] = (-np.pi, np.pi),
    figsize: tuple[float, float] = (6, 4),
    dpi: int = 120,
    add_colorbar: bool = True,
    hide_axes: bool = True,
) -> None:
    """Create an animated GIF of cumulative displacement.

    Parameters
    ----------
    ts_file : str
        Path to MintPy timeseries.h5 (or geo_timeseries.h5)
    out_gif : str
        Output GIF path
    mask_file : str | None
        Optional mask file. If None, pp.read_mask() will auto-search typical masks.
    disp_unit : {"cm","mm","m","radian",...}
        Display unit
    vlim : (float,float) | None
        Fixed color limits. If None, auto/percentile is used.
    vlim_percentile : (float,float) | None
        e.g., (2,98). Used only when vlim is None.
    cmap_name : str
        Colormap name. Diverging like "RdBu_r" is recommended.
    fps : int
        Frames per second.
    ref : {"first","date"}
        Reference policy: first acquisition or a specific date.
    ref_date : str | None
        "YYYYMMDD" if ref == "date".
    start_date : str | None
        "YYYYMMDD": frames before this date are excluded.
    wrap : bool
        Phase wrap display (not typical for displacement).
    wrap_range : (float,float)
        Wrap range for `wrap=True`.
    figsize : (float,float)
        Matplotlib figure size (in inches).
    dpi : int
        Figure DPI.
    add_colorbar : bool
        Draw colorbar on each frame.
    hide_axes : bool
        Hide axes/frames for clean map.
    """
    # 1) Read meta + date list
    obj = TsObj(ts_file)
    obj.open(print_msg=False)
    date_list = obj.dateList[:]                 # ['YYYYMMDD', ...]

    # --- start_date でトリミング ---
    if start_date is not None:
        if start_date not in date_list:
            raise ValueError(f"start_date={start_date} が timeseries 内にありません。")
        start_idx = date_list.index(start_date)
        date_list = date_list[start_idx:]

    dates, _ = ptime.date_list2vector(date_list)
    atr = readfile.read_attribute(ts_file)

    # 2) Read 3D stack (num_date, length, width)
    data, _ = readfile.read(ts_file, datasetName=date_list)

    # 3) Reference to first / specific date
    if ref == "first":
        # 先頭（start_date が指定されていれば start_date）が基準
        data = data - data[0, :, :]
        ref_str = dates[0].strftime("%Y-%m-%d")
    elif ref == "date":
        if (ref_date is None) or (ref_date not in date_list):
            raise ValueError("ref='date' を使う場合は、ref_date='YYYYMMDD' を date_list 内から指定してください。")
        ridx = date_list.index(ref_date)
        data = data - data[ridx, :, :]
        ref_str = dates[ridx].strftime("%Y-%m-%d")
    else:
        raise ValueError("ref must be 'first' or 'date'.")

    # 4) Mask
    mask = pp.read_mask(ts_file, mask_file=mask_file, datasetName='displacement', print_msg=False)[0]
    if mask is None:
        mask = np.ones(data.shape[-2:], np.bool_)
    stack = np.nansum(data, axis=0)
    mask[np.isnan(stack)] = False
    del stack

    # 5) Unit scaling & color limits
    data, disp_unit_out, _ = pp.scale_data2disp_unit(data, metadata=atr, disp_unit=disp_unit)

    if vlim is None:
        if vlim_percentile is not None:
            lo, hi = vlim_percentile
            vmin = float(np.nanpercentile(data, lo))
            vmax = float(np.nanpercentile(data, hi))
            vlim = (vmin, vmax)
        else:
            # MintPy auto (robust-ish)
            vlim = pp.auto_adjust_colormap_lut_and_disp_limit(
                data, num_multilook=10, print_msg=False
            )[1]

    # TwoSlopeNorm if symmetric around 0 (nice for subsidence/upheaval)
    use_two_slope = (vlim[0] < 0 < vlim[1]) and np.isclose(abs(vlim[0]), abs(vlim[1]), rtol=0.1, atol=0.0)
    norm = TwoSlopeNorm(vmin=vlim[0], vcenter=0.0, vmax=vlim[1]) if use_two_slope else None

    # 6) Frames -> GIF
    frames = []
    for i, d in enumerate(date_list):
        img = np.array(data[i])
        img[mask == 0] = np.nan
        if wrap:
            img = ut.wrap(img, wrap_range=wrap_range)

        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        im = ax.imshow(
            img,
            cmap=cmap_name,
            vmin=None if norm else vlim[0],
            vmax=None if norm else vlim[1],
            norm=norm,
        )
        if hide_axes:
            ax.set_axis_off()

        disp_date = dates[i].strftime("%Y-%m-%d")
        ax.set_title(f"N = {i}   Time = {disp_date}   (ref = {ref_str})", fontsize=10)

        if add_colorbar:
            cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            label = 'Amplitude' if atr.get('DATA_TYPE', '').startswith('complex') else 'Displacement'
            cbar.set_label(f"{label} [{disp_unit_out}]", fontsize=9)

        fig.tight_layout()
        # Render to array (no temp files)
        fig.canvas.draw()
        # Get RGBA buffer and drop alpha channel
        w, h = fig.canvas.get_width_height()
        buf = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
        buf = buf.reshape(h, w, 4)
        frame = buf[:, :, :3].copy()  # keep RGB only
        frames.append(frame)
        plt.close(fig)

    imageio.mimsave(out_gif, frames, duration=1.0 / fps)


def _parse_cli(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Make GIF from MintPy timeseries (cumulative displacement).")
    p.add_argument("ts_file")
    p.add_argument("out_gif")
    p.add_argument("--mask-file", default=None)
    p.add_argument("--disp-unit", default="cm", choices=["cm", "mm", "m", "radian"])
    p.add_argument("--cmap", default="RdBu_r")
    p.add_argument("--fps", type=int, default=5)
    p.add_argument("--ref", default="first", choices=["first", "date"])
    p.add_argument("--ref-date", default=None, help="YYYYMMDD (use with --ref date)")
    p.add_argument("--start-date", default=None, help="YYYYMMDD: ignore dates before this")  # ★ 追加
    p.add_argument("--wrap", action="store_true")
    p.add_argument("--wrap-range", nargs=2, type=float, default=[-np.pi, np.pi], metavar=("MIN", "MAX"))
    p.add_argument("--figsize", nargs=2, type=float, default=[6, 4], metavar=("W", "H"))
    p.add_argument("--dpi", type=int, default=120)
    p.add_argument("--no-colorbar", dest="add_colorbar", action="store_false")
    p.add_argument("--show-axes", dest="hide_axes", action="store_false")

    # vlim options (mutually exclusive: fixed vs percentile vs auto)
    group = p.add_mutually_exclusive_group()
    group.add_argument("--vlim", nargs=2, type=float, metavar=("MIN", "MAX"))
    group.add_argument("--vlim-percentile", nargs=2, type=float, metavar=("PLOW", "PHIGH"))

    args = p.parse_args(argv)
    return args


def _main(argv=None):
    args = _parse_cli(argv)
    make_cumdisp_gif(
        ts_file=args.ts_file,
        out_gif=args.out_gif,
        mask_file=args.mask_file,
        disp_unit=args.disp_unit,
        vlim=tuple(args.vlim) if args.vlim else None,
        vlim_percentile=tuple(args.vlim_percentile) if args.vlim_percentile else None,
        cmap_name=args.cmap,
        fps=args.fps,
        ref=args.ref,
        ref_date=args.ref_date,
        start_date=args.start_date,
        wrap=args.wrap,
        wrap_range=tuple(args.wrap_range),
        figsize=tuple(args.figsize),
        dpi=args.dpi,
        add_colorbar=args.add_colorbar,
        hide_axes=args.hide_axes,
    )


if __name__ == "__main__":
    _main()
