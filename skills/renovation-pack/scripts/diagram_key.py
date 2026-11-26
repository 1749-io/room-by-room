"""Draw a compact on-sheet key using the actual artists on a homeowner diagram."""
def draw_key(figure, axes, *, at, columns):
    """Collect labelled artists in draw order and share one key across comparable panels.

    Set an artist's label when drawing a meaningful symbol or line. Leave directly
    named elements and the background unlabelled. Use the same label for repeats.
    Coordinates for 'at' are fractions of the whole sheet.
    """
    symbols = {}
    for axis in axes:
        handles, labels = axis.get_legend_handles_labels()
        for handle, label in zip(handles, labels):
            symbols.setdefault(label, handle)
    if not symbols:
        raise ValueError("Label the symbols on the diagram before drawing its key.")
    legend = figure.legend(list(symbols.values()), list(symbols), loc="upper left",
                           bbox_to_anchor=at, ncol=columns, frameon=False, borderaxespad=0,
                           borderpad=0, handlelength=1.8, handletextpad=.65, columnspacing=1.7,
                           labelspacing=.6, fontsize=9)
    return legend


def check_key(figure, panels, legend):
    """Check the plotted symbols are keyed and the key is visible at export size."""
    expected = {label for panel in panels for label in panel.get_legend_handles_labels()[1]}
    shown = [entry.get_text() for entry in legend.get_texts()]
    if not expected or expected != set(shown) or len(shown) != len(expected):
        raise ValueError("The key must name each plotted symbol once.")
    figure.canvas.draw()
    area = legend.get_window_extent(figure.canvas.get_renderer())
    if not figure.bbox.contains(*area.min) or not figure.bbox.contains(*area.max):
        raise ValueError("The key extends beyond the sheet.")
    if any(area.overlaps(axis.get_window_extent()) for axis in panels):
        raise ValueError("Place the key in its own margin outside the drawing.")
