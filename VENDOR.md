# Bundled source

`Relation/` contains unmodified source files from https://github.com/hhyqhh/Relation at commit `03c19d4280b38230e0852054922072f5aa6dcdf5`.

The upstream license is preserved in `Relation/LICENSE.txt` (LGPL v3 text). Upstream authors retain their rights. This project adds experiment wrappers; it does not claim authorship of the bundled source.

Git metadata, bytecode caches, .DS_Store, generated egg-info metadata and documentation images were omitted. No upstream Python source or YAML configuration was edited. `vendor_manifest.json` lists the included files and SHA256 values with CRLF normalized to LF, allowing Windows Git line-ending conversion. It is an integrity record, not experiment data.

The added experiment uses the first version's current-to-rand CoDE strategy. The later current-to-best comparison and DE diagnostic are not included. The pinned pymoo version retains its original donor sampling behavior for reproducibility; this package does not incorporate the later proposed correction.

`engine.py`, `components.py`, and `problems.py` are copied unchanged from the first experiment. Only packaging, preparation and reporting were adjusted to remove Git, MATLAB and PDF dependencies. No measured results are distributed.
