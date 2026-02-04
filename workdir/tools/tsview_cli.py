#!/usr/bin/env python3
import os
import sys
from mintpy.utils import arg_utils

EXAMPLE = """example:
  tsview.py timeseries.h5
  tsview.py timeseries.h5 --wrap
  tsview.py timeseries.h5 --yx 300 400 --zero-first --nodisplay
  tsview.py geo_timeseries.h5 --lalo 33.250 131.665 --nodisplay
  tsview.py slcStack.h5 -u dB -v 20 60 -c gray
  tsview.py timeseries_ERA5_ramp_demErr.h5 timeseries_ERA5_ramp.h5 timeseries_ERA5.h5 timeseries.h5 --off 5

  # ★静的 idx 表示（スライダー無し）
  tsview.py timeseries.h5 --idx 42 --no-slider
"""

def create_parser(subparsers=None):
    synopsis = 'Interactive time-series viewer'
    epilog = EXAMPLE
    name = __name__.split('.')[-1]
    parser = arg_utils.create_argument_parser(
        name, synopsis=synopsis, description=synopsis, epilog=epilog, subparsers=subparsers)

    parser.add_argument('file', nargs='+', help='time-series file(s)')
    parser.add_argument('--label', dest='file_label', nargs='*')
    parser.add_argument('--ylim', dest='ylim', nargs=2, metavar=('YMIN', 'YMAX'), type=float)
    parser.add_argument('--tick-right', dest='tick_right', action='store_true')
    parser.add_argument('-l','--lookup', dest='lookup_file', type=str)
    parser.add_argument('--no-show-img','--not-show-image', dest='disp_fig_img', action='store_false')

    # ✅ -n に加えて --idx を正式対応
    parser.add_argument('-n','--idx', dest='idx', metavar='NUM', type=int,
                        help='Epoch/slice index for display.')

    parser.add_argument('--error', dest='error_file')

    # ✅ スライダー無効化フラグ
    parser.add_argument('--no-slider', dest='no_slider', action='store_true',
                        help='Disable time slider and keyboard navigation.')

    # time info
    parser.add_argument('--start-date', dest='start_date', type=str)
    parser.add_argument('--end-date', dest='end_date', type=str)
    parser.add_argument('--exclude','--ex', dest='ex_date_list', nargs='*', default=['exclude_date.txt'])
    parser.add_argument('--zf','--zero-first', dest='zero_first', action='store_true')
    parser.add_argument('--off','--offset', dest='offset', type=float)

    parser.add_argument('--noverbose', dest='print_msg', action='store_false')

    # temporal model fitting
    parser.add_argument('--nomodel','--nofit', dest='plot_model', action='store_false')
    parser.add_argument('--plot-model-conf-int','--plot-fit-conf-int',
                        dest='plot_model_conf_int', action='store_true')

    # 追加の共通引数グループ
    parser = arg_utils.add_timefunc_argument(parser)
    parser = arg_utils.add_data_disp_argument(parser)
    parser = arg_utils.add_dem_argument(parser)
    parser = arg_utils.add_figure_argument(parser, figsize_img=True)
    parser = arg_utils.add_gnss_argument(parser)
    parser = arg_utils.add_mask_argument(parser)
    parser = arg_utils.add_map_argument(parser)
    parser = arg_utils.add_memory_argument(parser)
    parser = arg_utils.add_reference_argument(parser)
    parser = arg_utils.add_save_argument(parser)
    parser = arg_utils.add_subset_argument(parser)

    # Pixel
    pixel = parser.add_argument_group('Pixel Input')
    pixel.add_argument('--yx', type=int, metavar=('Y','X'), nargs=2)
    pixel.add_argument('--lalo', type=float, metavar=('LAT','LON'), nargs=2)
    pixel.add_argument('--marker', type=str, default='o')
    pixel.add_argument('--ms','--markersize', dest='marker_size', type=float, default=6.0)
    pixel.add_argument('--lw','--linewidth', dest='linewidth', type=float, default=0)
    pixel.add_argument('--ew','--edgewidth', dest='edge_width', type=float, default=1.0)

    return parser

def cmd_line_parse(iargs=None):
    parser = create_parser()
    inps = parser.parse_args(args=iargs)
    inps.argv = iargs or sys.argv[1:]

    if inps.gnss_component:
        raise NotImplementedError(f'--gnss-comp is not supported for {os.path.basename(__file__)}')

    if inps.file_label and len(inps.file_label) != len(inps.file):
        raise Exception('input number of labels != number of files.')

    if not inps.save_fig and (inps.outfile or not inps.disp_fig):
        inps.save_fig = True

    if inps.flip_lr or inps.flip_ud:
        inps.auto_flip = False

    if inps.ylim:
        inps.ylim = sorted(inps.ylim)

    if inps.zero_mask:
        inps.mask_file = 'no'

    if not inps.disp_fig_img and (not inps.yx and not inps.lalo):
        inps.disp_fig_img = True
        print('WARNING: --yx/lalo is required for --no-show-img but NOT found! Ignore it and continue')

    inps.disp_unit = inps.disp_unit if inps.disp_unit else 'cm'
    inps.colormap  = inps.colormap  if inps.colormap  else 'jet'
    inps.fig_size  = inps.fig_size  if inps.fig_size  else [8.0, 4.5]

    if not hasattr(inps, 'no_slider'):
        inps.no_slider = False

    return inps

def main(iargs=None):
    inps = cmd_line_parse(iargs)
    # Viewer はまずローカル tools を優先、無ければ MintPy 本体へフォールバック
    try:
        from tools.plot_ts import timeseriesViewer
    except Exception:
        from mintpy.tsview import timeseriesViewer

    obj = timeseriesViewer(inps)
    obj.open()
    obj.plot()

if __name__ == '__main__':
    main(sys.argv[1:])
