"""
ec61.py -- shared parsing / loading for the ElectroCom-61 benchmark study.

Every analysis script in scripts/ imports this module so that filename parsing,
CSV normalisation and the image<->CSV join are defined in EXACTLY one place.
If two scripts parsed filenames differently their numbers would not reconcile
and neither could be trusted, so all of that logic lives here.

Standard library only -- no pandas, no numpy. A reviewer needs nothing but a
Python 3 interpreter to reproduce any result in runs/.
"""

import csv
import hashlib
import json
import os
import platform
import re
import sys
from datetime import datetime

# --------------------------------------------------------------------------
# Repository layout
# --------------------------------------------------------------------------

# This file lives in <repo>/scripts/, so the repo root is one directory up.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
DATASET_DIR = os.path.join(DATA_DIR, "ElectroCom-61_v2")
METADATA_CSV = os.path.join(DATA_DIR, "Metadata_ElectroCom61.csv")
RUNS_DIR = os.path.join(REPO_ROOT, "runs")

# Built by scripts/build_corrected_dataset.py from the released manifest. Like
# DATASET_DIR it is git-ignored, so a fresh checkout does not have it.
CORRECTED_DIR = os.path.join(DATA_DIR, "ElectroCom-61_corrected")

# Directory names on disk. Kept as a tuple so iteration order is fixed and
# every output table has columns in the same order across every run.
SPLITS = ("train", "valid", "test")

# --------------------------------------------------------------------------
# Required inputs that are NOT in the repository
# --------------------------------------------------------------------------
#
# WHY THIS EXISTS. The datasets are git-ignored on purpose -- they are inputs to
# this study, not products of it, and they are reproduced by download
# instruction. So a fresh checkout legitimately cannot run every script. What is
# NOT legitimate is how that used to look: a clean-checkout run on 2026-08-15
# found fifteen scripts crashing with an unhandled traceback on the missing
# tree, among them build_corrected_dataset.py -- the script the well-behaved
# ones tell the reader to run next. Following the repository's own instructions
# produced a stack trace.
#
# Every script that needs one of these now calls require_inputs() first and
# exits non-zero with a message naming the tree and how to obtain it. The check
# lives here so there is one message per input rather than fifteen.

DATASET_V2_DOI = "10.17632/6scy6h8sjz.2"
DATASET_V2_URL = "https://data.mendeley.com/datasets/6scy6h8sjz/2"

# name -> (path, what it is, how to obtain it)
_REQUIRED_INPUTS = {
    "dataset_v2": (
        DATASET_DIR,
        "the ElectroCom61 v2 dataset tree",
        "Download doi:%s from %s and unpack it there. README.md, section "
        "'Getting the data', gives the exact layout expected."
        % (DATASET_V2_DOI, DATASET_V2_URL)),
    "corrected": (
        CORRECTED_DIR,
        "the corrected-split dataset tree",
        "Build it: python scripts/build_corrected_dataset.py"),
    "metadata": (
        METADATA_CSV,
        "the metadata CSV shipped inside the v2 archive",
        "It ships with doi:%s; unpack the archive so the CSV lands in data/."
        % DATASET_V2_DOI),
}


def require_inputs(*names, **kwargs):
    """Return an exit code: 0 if every named input is present, 1 if not.

    On failure the message is already on stderr, naming each missing path and
    the command or download that produces it. Callers do:

        rc = ec61.require_inputs("dataset_v2")
        if rc:
            return rc

    Nothing is raised: a missing dataset is an ordinary, expected condition in
    a fresh checkout, not a bug to be traced.
    """
    stream = kwargs.pop("stream", None) or sys.stderr
    if kwargs:
        raise TypeError("unexpected keyword arguments: %s" % sorted(kwargs))

    missing = []
    for name in names:
        try:
            path, what, how = _REQUIRED_INPUTS[name]
        except KeyError:
            raise KeyError("unknown required input %r; known: %s"
                           % (name, sorted(_REQUIRED_INPUTS)))
        # A file requirement needs isfile; a tree needs isdir. Checking for
        # mere existence would let a stray file named like the tree through.
        ok = os.path.isfile(path) if os.path.splitext(path)[1] else \
            os.path.isdir(path)
        if not ok:
            missing.append((path, what, how))

    if not missing:
        return 0

    for path, what, how in missing:
        stream.write("missing input: %s\n" % path)
        stream.write("  this is %s.\n" % what)
        stream.write("  %s\n" % how)
    return 1

# --------------------------------------------------------------------------
# Filename parsing
# --------------------------------------------------------------------------

# Roboflow rewrites every exported file as:  <stem>_<EXT>.rf.<32 hex>.<ext>
# e.g.  IMG_5126_JPG.rf.86ccf99f5ec931ec6783ddf155143993.jpg
# The tail is rigid (literal ".rf.", exactly 32 hex chars, then an extension),
# so the greedy .+ for the stem backtracks to exactly the right split point.
ROBOFLOW_RE = re.compile(
    r"^(?P<stem>.+)_(?P<orig_ext>jpg|jpeg|png)\.rf\.(?P<hash>[0-9a-f]{32})\.(?P<ext>jpg|jpeg|png)$",
    re.IGNORECASE,
)

# Filename families, tried IN ORDER -- most specific first.
#
# This ordering is load-bearing. `IMG20240228131921_01` also matches the
# less specific ts_compact pattern if that pattern is not anchored at the end;
# every pattern below IS anchored with $, but keeping the sub-indexed variant
# ahead of the plain one documents the hazard and makes the order safe even if
# somebody later relaxes an anchor.
#
# Each entry: (family_name, compiled_regex)
FAMILY_PATTERNS = (
    # IMG_20240219_113620   -- underscore-delimited timestamp
    ("ts_underscore", re.compile(r"^IMG_(?P<date>\d{8})_(?P<time>\d{6})$")),
    # IMG20240228131921_01  -- compact timestamp PLUS a burst sub-index
    ("ts_compact_sub", re.compile(r"^IMG(?P<date>\d{8})(?P<time>\d{6})_(?P<sub>\d{2})$")),
    # IMG20240219113638     -- compact timestamp
    ("ts_compact", re.compile(r"^IMG(?P<date>\d{8})(?P<time>\d{6})$")),
    # IMG_5126              -- sequential camera counter, NO timestamp at all
    ("counter", re.compile(r"^IMG_(?P<counter>\d{4})$")),
)

# Families from which a capture datetime can be recovered. The `counter`
# family cannot be placed on a timeline and must be excluded from any
# timestamp-based analysis -- and reported as excluded, never silently dropped.
TIMESTAMPED_FAMILIES = frozenset({"ts_underscore", "ts_compact_sub", "ts_compact"})


class ImageRecord(object):
    """One image on disk, with everything derived from its filename.

    Attributes that may legitimately be None:
      dt       -- None for the `counter` family (no timestamp encoded)
      sub      -- None unless the family is ts_compact_sub
      counter  -- None unless the family is `counter`
      csv_row  -- None when the image has no matching Metadata row
    """

    __slots__ = (
        "filename", "split", "stem", "family", "date_str", "time_str",
        "dt", "epoch", "sub", "counter", "csv_row", "label_path",
    )

    def __init__(self, filename, split, stem, family):
        self.filename = filename
        self.split = split
        self.stem = stem
        self.family = family
        self.date_str = None
        self.time_str = None
        self.dt = None
        self.epoch = None       # seconds since epoch, for cheap gap arithmetic
        self.sub = None
        self.counter = None
        self.csv_row = None
        self.label_path = None

    @property
    def device_csv(self):
        """DEVICE_NAME from the metadata CSV, or None if the row is missing."""
        if self.csv_row is None:
            return None
        return self.csv_row.get("DEVICE_NAME")

    @property
    def device_key(self):
        """Grouping key for per-device burst clustering.

        Prefers the CSV device name. Falls back to the filename family when
        the CSV has no row for this image -- clustering across two physically
        different cameras would manufacture bursts that never happened, so a
        conservative fallback (which over-splits rather than over-merges) is
        the safe direction to err in.
        """
        dev = self.device_csv
        if dev:
            return dev
        return "FAMILY:" + self.family


def parse_stem(filename):
    """Strip the Roboflow suffix from an exported filename.

    Returns the original capture-time stem, or None if the filename does not
    have the expected Roboflow shape (caller must surface that, not ignore it).
    """
    m = ROBOFLOW_RE.match(filename)
    if m is None:
        return None
    return m.group("stem")


def parse_stem_tolerant(filename):
    """Recover a capture-time stem from a filename that may NOT be a Roboflow export.

    `parse_stem` deliberately returns None for anything that is not a Roboflow
    export, because inside the v2 dataset a non-matching name is a data problem
    worth surfacing. But a dataset downloaded straight from Mendeley was never
    passed through Roboflow, so its files are named `IMG20241118101346.jpg` with
    no `.rf.<hash>` tail -- and there, a None would look like a parse failure
    when it is actually the normal case.

    Returns (stem, route) where route is one of:
      'roboflow'  -- the Roboflow tail was present and has been stripped
      'raw'       -- no Roboflow tail; the extension alone was stripped

    The route is returned rather than discarded so callers can report HOW each
    filename was read. If a v1-vs-v2 comparison silently mixed the two routes it
    could manufacture agreement (or disagreement) that is an artefact of parsing
    rather than a fact about the data.
    """
    stem = parse_stem(filename)
    if stem is not None:
        return stem, "roboflow"
    # Strip a single trailing image extension, case-insensitively. Anything
    # else in the name is left exactly as-is.
    return re.sub(r"\.(jpg|jpeg|png)$", "", filename, flags=re.IGNORECASE), "raw"


def classify_stem(stem):
    """Map a stem to (family_name, regex match), or ('unparsed', None)."""
    for family, pattern in FAMILY_PATTERNS:
        m = pattern.match(stem)
        if m is not None:
            return family, m
    return "unparsed", None


def _build_record(filename, split):
    """Construct a fully populated ImageRecord from a filename. Never raises."""
    stem = parse_stem(filename)
    if stem is None:
        # Filename did not match the Roboflow export pattern at all. Keep the
        # raw name as the stem so it still appears in output tables.
        rec = ImageRecord(filename, split, filename, "unparsed")
        return rec

    family, m = classify_stem(stem)
    rec = ImageRecord(filename, split, stem, family)

    if family in TIMESTAMPED_FAMILIES:
        rec.date_str = m.group("date")
        rec.time_str = m.group("time")
        try:
            rec.dt = datetime.strptime(rec.date_str + rec.time_str, "%Y%m%d%H%M%S")
            # Treat the wall-clock string as naive local time. Only DIFFERENCES
            # between timestamps from the same device are ever used, so the
            # absolute zero point and timezone are irrelevant.
            rec.epoch = (rec.dt - datetime(1970, 1, 1)).total_seconds()
        except ValueError:
            # e.g. an impossible date like 20240230; keep the family but leave
            # dt as None so downstream code excludes it explicitly.
            rec.dt = None
            rec.epoch = None
        if family == "ts_compact_sub":
            rec.sub = int(m.group("sub"))
    elif family == "counter":
        rec.counter = int(m.group("counter"))

    return rec


def load_images(dataset_dir=DATASET_DIR, splits=SPLITS):
    """Enumerate every image in every split and parse its filename.

    Returns a list of ImageRecord sorted by (split, filename) so that all
    downstream output is deterministic regardless of filesystem ordering.
    """
    records = []
    for split in splits:
        img_dir = os.path.join(dataset_dir, split, "images")
        lbl_dir = os.path.join(dataset_dir, split, "labels")
        if not os.path.isdir(img_dir):
            # A backstop, not the primary check. Scripts call require_inputs()
            # first and exit cleanly; this fires only for a caller that did
            # not, so it repeats the remedy rather than just the path.
            raise IOError(
                "missing image directory: %s\nThis is part of %s. %s"
                % (img_dir, _REQUIRED_INPUTS["dataset_v2"][1],
                   _REQUIRED_INPUTS["dataset_v2"][2]))
        for filename in sorted(os.listdir(img_dir)):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            rec = _build_record(filename, split)
            # YOLO label files mirror the image filename with a .txt extension.
            base = filename.rsplit(".", 1)[0]
            candidate = os.path.join(lbl_dir, base + ".txt")
            rec.label_path = candidate if os.path.isfile(candidate) else None
            records.append(rec)
    # Sort by split in the canonical SPLITS order, then filename.
    split_rank = {s: i for i, s in enumerate(splits)}
    records.sort(key=lambda r: (split_rank.get(r.split, 99), r.filename))
    return records


# --------------------------------------------------------------------------
# Metadata CSV
# --------------------------------------------------------------------------

def _csv_key(image_name):
    """Normalise a CSV IMAGE_NAME into a join key matching an image stem.

    Only the EXTENSION is treated case-insensitively (the CSV mixes '.jpg' and
    '.JPG'). The stem itself is compared case-sensitively, because a stem that
    differs only by case would be a genuine data problem worth surfacing.
    """
    return re.sub(r"\.(jpg|jpeg|png)$", "", image_name, flags=re.IGNORECASE)


def load_metadata(metadata_csv=METADATA_CSV):
    """Load the metadata CSV into {join_key: row_dict}.

    EVERY field value is whitespace-stripped on the way in. The raw file
    contains both 'REDMI' and 'REDMI ' and both 'Wooden' and 'Wooden ', which
    would otherwise appear as four distinct categories in a group-by.

    Returns (rows_by_key, duplicate_keys, n_data_rows).
    """
    rows_by_key = {}
    duplicate_keys = []
    n_data_rows = 0

    # newline='' per the csv module's documented requirement; utf-8-sig drops a
    # BOM if the file has one so the first header name is not mangled.
    with open(metadata_csv, "r", newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            n_data_rows += 1
            # Strip whitespace from both keys and values. A None value appears
            # when a row has fewer fields than the header.
            row = {}
            for k, v in raw.items():
                if k is None:
                    continue
                row[k.strip()] = v.strip() if isinstance(v, str) else v
            key = _csv_key(row.get("IMAGE_NAME", ""))
            if key in rows_by_key:
                duplicate_keys.append(key)
            rows_by_key[key] = row

    return rows_by_key, duplicate_keys, n_data_rows


def attach_metadata(records, rows_by_key):
    """Attach CSV rows to image records in place. Returns (n_joined, n_missing)."""
    n_joined = 0
    n_missing = 0
    for rec in records:
        row = rows_by_key.get(rec.stem)
        if row is None:
            n_missing += 1
        else:
            rec.csv_row = row
            n_joined += 1
    return n_joined, n_missing


# --------------------------------------------------------------------------
# YOLO label files
# --------------------------------------------------------------------------

def load_boxes(label_path):
    """Parse a YOLO label file into [(class_id, cx, cy, w, h), ...].

    Coordinates stay in the normalised 0-1 space YOLO uses, which makes every
    downstream geometric comparison resolution-independent -- important here
    because Roboflow stretched all images to 640x640.

    Malformed lines are skipped rather than raising; the caller reports counts.
    """
    boxes = []
    if label_path is None:
        return boxes
    with open(label_path, "r", encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) != 5:
                continue  # not a standard YOLO detection line
            try:
                cid = int(parts[0])
                cx, cy, w, h = (float(p) for p in parts[1:])
            except ValueError:
                continue
            boxes.append((cid, cx, cy, w, h))
    return boxes


# --------------------------------------------------------------------------
# Run directories and provenance
# --------------------------------------------------------------------------

def make_run_dir(name, runs_dir=RUNS_DIR, when=None):
    """Create runs/<YYYYMMDD>_<name>/ and return its path.

    Per the project rules a previous run is NEVER overwritten. If the target
    directory already exists a numeric suffix (_02, _03, ...) is appended until
    an unused name is found.
    """
    stamp = (when or datetime.now()).strftime("%Y%m%d")
    base = os.path.join(runs_dir, "%s_%s" % (stamp, name))
    path = base
    n = 2
    while os.path.exists(path):
        path = "%s_%02d" % (base, n)
        n += 1
    os.makedirs(path)
    return path


def _sha256_file(path):
    """SHA-256 of a file, so a run can be tied to the exact script that made it."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_config(run_dir, script_path, params, extra=None):
    """Write config.json capturing everything needed to reproduce this run.

    The project rule is that no number may be reported without the config that
    produced it, so this is called by every script before it writes any table.
    """
    cfg = {
        "script": os.path.basename(script_path),
        "script_sha256": _sha256_file(script_path),
        "module_sha256": _sha256_file(os.path.abspath(__file__)),
        "run_started_utc": datetime.utcnow().isoformat() + "Z",
        "python_version": sys.version,
        "platform": platform.platform(),
        "repo_root": REPO_ROOT,
        "dataset_dir": DATASET_DIR,
        "metadata_csv": METADATA_CSV,
        "params": params,
    }
    if extra:
        cfg.update(extra)
    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(cfg, fh, indent=2, sort_keys=True)
    return cfg


def write_csv(path, header, rows):
    """Write a CSV with a fixed header. Rows are written exactly as given.

    TWO SEPARATE NEWLINE SETTINGS, AND BOTH ARE LOAD-BEARING.

    `newline=""` on the file is what the csv module requires: without it, the
    terminator csv writes would be translated a SECOND time by the text layer
    and every row would end "\r\r\n" on Windows.

    `lineterminator="\n"` on the writer is what makes the output LF. The csv
    module's default is "\r\n" on every platform, independently of how the file
    was opened, so `newline=""` alone yields CRLF. That went unnoticed until
    2026-08-16 because core.autocrlf checked these files out as CRLF too, so
    regenerating one matched what was on disk. Pinning *.csv to eol=lf in
    .gitattributes removed that coincidence and left master_results.csv
    differing from HEAD in 1904 of its 2351 bytes -- every line, none of the
    content.
    """
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        for row in rows:
            w.writerow(row)


# --------------------------------------------------------------------------
# The master results table
# --------------------------------------------------------------------------

MASTER_CSV = os.path.join(DATA_DIR, "master_results.csv")

# Runs that must never be aggregated with the benchmark. Membership is declared
# here, by slug, and is NEVER inferred from the numbers -- a run is diverged
# because we can say why, not because its mAP looked low enough to disown.
#
#   rtdetr_l_pub -- RT-DETR-l on the published split at lr0=0.01, the YOLO
#   learning rate. All three training loss terms went NaN at epoch 7 and the
#   run was stopped at 19. It is retained as the evidence for the learning-rate
#   deviation described in the paper, not as a result.
DIVERGED_RUNS = ("rtdetr_l_pub",)

# The benchmark proper: five architectures times two splits.
N_BENCHMARK_ROWS = 10

INCLUSION_BENCHMARK = "benchmark"
INCLUSION_DIVERGED = "diverged"


def load_master_rows(path=MASTER_CSV):
    """Every row of master_results.csv, diverged runs included."""
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def load_benchmark_rows(path=MASTER_CSV, expected=N_BENCHMARK_ROWS):
    """The benchmark rows only -- the ONLY loader an aggregate may use.

    Every figure, table and derived statistic in this study reads the master
    table through here. Three things are enforced, and each is enforced because
    the alternative fails silently:

      1. Rows are filtered to inclusion == "benchmark". A diverged run averaged
         into a mean does not announce itself; it just moves the number.

      2. The surviving count must equal `expected`. Filtering alone is not
         enough -- if a row is added later without an inclusion value, or the
         column is dropped by an editing accident, the filter would quietly
         return the wrong set. This turns that into a crash.

      3. (model, split_set) must be unique. The diverged run shares BOTH with
         rtdetr_l_pub_lr1e4, and consumers that index by that pair would
         otherwise keep whichever row happened to be read last -- an outcome
         that depends on file ordering rather than on intent.

    A missing `inclusion` column is an error rather than a default, because
    defaulting would make an out-of-date table look healthy.
    """
    rows = load_master_rows(path)
    if not rows:
        raise ValueError("%s has no rows" % path)
    if "inclusion" not in rows[0]:
        raise ValueError(
            "%s has no `inclusion` column. Regenerate it with "
            "scripts/collect_results.py -- an unlabelled table cannot be "
            "filtered safely." % path)

    kept = [r for r in rows if r["inclusion"] == INCLUSION_BENCHMARK]
    if len(kept) != expected:
        raise ValueError(
            "%s: expected %d benchmark rows, found %d. Rows present: %s"
            % (path, expected, len(kept),
               ", ".join("%s=%s" % (r.get("run"), r.get("inclusion"))
                         for r in rows)))

    seen = {}
    for r in kept:
        key = (r["model"], r["split_set"])
        if key in seen:
            raise ValueError(
                "%s: duplicate (model, split_set) among benchmark rows: %s "
                "appears as both %s and %s. Indexing by that pair would keep "
                "only one of them." % (path, key, seen[key], r["run"]))
        seen[key] = r["run"]
    return kept


def counts_table(records, key_fn, splits=SPLITS):
    """Group records by key_fn and count per split.

    Returns (sorted_keys, {key: {split: count}}). Keys sort alphabetically so
    table row order is stable between runs.
    """
    table = {}
    for rec in records:
        key = key_fn(rec)
        bucket = table.setdefault(key, {s: 0 for s in splits})
        bucket[rec.split] = bucket.get(rec.split, 0) + 1
    return sorted(table.keys(), key=lambda k: str(k)), table
