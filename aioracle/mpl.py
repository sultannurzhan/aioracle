"""Matplotlib/Qt backend wiring.

Centralizing this prevents accidentally mixing Qt backends across modules.
"""

import matplotlib


def get_mpl():
	"""Return (FigureCanvas, Figure, mdates) with backend imports deferred.

	This avoids importing Qt backend modules before a QApplication exists.
	"""

	# Configure the Qt backend only when needed (ideally after QApplication exists).
	matplotlib.use("QtAgg", force=True)

	from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas  # noqa: E402
	from matplotlib.figure import Figure  # noqa: E402
	import matplotlib.dates as mdates  # noqa: E402

	return FigureCanvas, Figure, mdates
