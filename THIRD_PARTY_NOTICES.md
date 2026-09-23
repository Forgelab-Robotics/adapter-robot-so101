# Third-party notices

The repository's original Python code, configuration, workflows, and
documentation are licensed under Apache License 2.0 unless a file or directory
states otherwise. The following bundled assets and vendored code retain their
upstream licenses.

## SO-ARM100 model assets

- Paths: `assets/mjcf/`, `assets/glb/`, `assets/usd/`
- Source: [SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100), commit
  `eecbe3e0a9ebb23e25ad7b2759b03884c6660903`
- License: Apache-2.0

The GLB and USD files are converted forms of the MuJoCo model and retain the
same upstream attribution. The PNG images in `assets/png/` are renders derived
from the model.

## Runtime dependencies

Python dependencies are not vendored into this repository. Their licenses are
provided by their respective distributions, including:

- `dora-rs`: MIT (according to the installed PyPI distribution metadata)
- `forge-common`, `forge-msgs`, `forge-robot`: see their PyPI distributions
- `mujoco`: Apache-2.0
- `opencv-python`: Apache-2.0
- `pyserial`: BSD-3-Clause
- `Typer`: MIT
- `websockets`: BSD-3-Clause
