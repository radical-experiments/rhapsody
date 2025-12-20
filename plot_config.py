"""
Centralized plotting configuration for RHAPSODY experiments.
Ensures consistent styling across all plots for publication.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt

# -----------------------------
# Publication-quality settings
# -----------------------------

# Figure dimensions (optimized for 4-panel subfigure layout at 0.24\linewidth each)
# Using consistent aspect ratio for all plots
FIGURE_WIDTH = 3.5   # inches
FIGURE_HEIGHT = 2.8  # inches (increased for better readability)
FIGURE_SIZE = (FIGURE_WIDTH, FIGURE_HEIGHT)

# DPI settings
DPI = 600

# Font settings (optimized for strong publication-quality appearance)
FONT_FAMILY = 'sans-serif'
FONT_SANS_SERIF = ['Arial', 'Helvetica', 'DejaVu Sans']
FONT_SIZE_BASE = 11
FONT_SIZE_TITLE = 12
FONT_SIZE_LABEL = 11
FONT_SIZE_TICK = 10
FONT_SIZE_LEGEND = 10
FONT_SIZE_ANNOTATION = 9

# Line and marker settings
LINE_WIDTH = 2.0
MARKER_SIZE = 7
CAPSIZE = 4

# Grid settings
GRID_ALPHA = 0.3
GRID_LINESTYLE = '--'
GRID_LINEWIDTH = 0.6

# Tight layout settings
TIGHT_LAYOUT_PAD = 0.2
BBOX_INCHES = 'tight'
PAD_INCHES = 0.02


def configure_matplotlib():
    """
    Configure matplotlib with publication-quality settings.
    Call this function at the start of your plotting script.
    """
    # Font settings
    mpl.rcParams['font.family'] = FONT_FAMILY
    mpl.rcParams['font.sans-serif'] = FONT_SANS_SERIF
    mpl.rcParams['font.size'] = FONT_SIZE_BASE

    # Axes settings
    mpl.rcParams['axes.titlesize'] = FONT_SIZE_TITLE
    mpl.rcParams['axes.labelsize'] = FONT_SIZE_LABEL
    mpl.rcParams['axes.titleweight'] = 'bold'
    mpl.rcParams['axes.labelweight'] = 'bold'
    mpl.rcParams['axes.linewidth'] = 1.0

    # Tick settings
    mpl.rcParams['xtick.labelsize'] = FONT_SIZE_TICK
    mpl.rcParams['ytick.labelsize'] = FONT_SIZE_TICK
    mpl.rcParams['xtick.major.width'] = 1.0
    mpl.rcParams['ytick.major.width'] = 1.0
    mpl.rcParams['xtick.minor.width'] = 0.8
    mpl.rcParams['ytick.minor.width'] = 0.8
    mpl.rcParams['xtick.major.size'] = 4.5
    mpl.rcParams['ytick.major.size'] = 4.5

    # Legend settings
    mpl.rcParams['legend.fontsize'] = FONT_SIZE_LEGEND
    mpl.rcParams['legend.frameon'] = True
    mpl.rcParams['legend.framealpha'] = 0.9
    mpl.rcParams['legend.edgecolor'] = 'gray'

    # Line settings
    mpl.rcParams['lines.linewidth'] = LINE_WIDTH
    mpl.rcParams['lines.markersize'] = MARKER_SIZE

    # Grid settings
    mpl.rcParams['grid.alpha'] = GRID_ALPHA
    mpl.rcParams['grid.linestyle'] = GRID_LINESTYLE
    mpl.rcParams['grid.linewidth'] = GRID_LINEWIDTH

    # Figure settings
    mpl.rcParams['figure.dpi'] = 100  # Screen display
    mpl.rcParams['savefig.dpi'] = DPI  # Saved figure
    mpl.rcParams['figure.figsize'] = FIGURE_SIZE

    # Use Type 1 fonts for better compatibility with publishers
    mpl.rcParams['pdf.fonttype'] = 42
    mpl.rcParams['ps.fonttype'] = 42


def save_figure(fig, filename, dpi=None, bbox_inches=None, pad_inches=None):
    """
    Save a figure with consistent settings.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The figure to save
    filename : str
        Output filename (can be .png, .pdf, .svg, etc.)
    dpi : int, optional
        Resolution (default: DPI constant)
    bbox_inches : str, optional
        Bounding box setting (default: BBOX_INCHES constant)
    pad_inches : float, optional
        Padding around figure (default: PAD_INCHES constant)
    """
    if dpi is None:
        dpi = DPI
    if bbox_inches is None:
        bbox_inches = BBOX_INCHES
    if pad_inches is None:
        pad_inches = PAD_INCHES

    fig.tight_layout(pad=TIGHT_LAYOUT_PAD)
    fig.savefig(filename, dpi=dpi, bbox_inches=bbox_inches, pad_inches=pad_inches)
    print(f"Figure saved to: {filename}")


def create_figure(nrows=1, ncols=1, **kwargs):
    """
    Create a figure with consistent size settings.

    Parameters
    ----------
    nrows : int
        Number of rows
    ncols : int
        Number of columns
    **kwargs : dict
        Additional arguments passed to plt.subplots()

    Returns
    -------
    fig, ax : matplotlib figure and axes
    """
    # Override figsize if not provided
    if 'figsize' not in kwargs:
        kwargs['figsize'] = FIGURE_SIZE

    return plt.subplots(nrows, ncols, **kwargs)
