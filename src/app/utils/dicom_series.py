"""Detect distinct DICOM series inside a (possibly nested) CT folder.

A folder a user points Sybil-Epi at can contain more than one series (e.g.
contrast and non-contrast acquisitions from the same study, each in its own
sub-folder or all mixed together). Sybil needs a single, unambiguous series
of slices, so callers use this to find out whether a choice is needed and,
if so, what each candidate series actually is.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pydicom
import pydicom.errors

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class DicomSeries:
    series_uid: str
    description: str
    series_number: int | None
    files: list[str]

    @property
    def slice_count(self) -> int:
        return len(self.files)

    @property
    def label(self) -> str:
        return f"{self.description} - {self.slice_count} slices"


def find_dicom_series(folder: Path) -> list[DicomSeries]:
    """Group every DICOM file under *folder* by SeriesInstanceUID.

    Walks the folder recursively (series are often split into sub-folders)
    and reads only the header of each file (``stop_before_pixels``) for
    speed. Non-DICOM files are silently skipped. Series are returned sorted
    by SeriesNumber when available, otherwise by description.
    """
    by_uid: dict[str, DicomSeries] = {}

    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue

        try:
            ds = pydicom.dcmread(str(path), stop_before_pixels=True)
        except (pydicom.errors.InvalidDicomError, OSError):
            continue

        uid = getattr(ds, "SeriesInstanceUID", None)
        if not uid:
            continue

        series = by_uid.get(uid)
        if series is None:
            description = str(getattr(ds, "SeriesDescription", "") or "").strip()
            series = DicomSeries(
                series_uid=uid,
                description=description or "Unnamed series",
                series_number=getattr(ds, "SeriesNumber", None),
                files=[],
            )
            by_uid[uid] = series

        series.files.append(str(path))

    return sorted(
        by_uid.values(),
        key=lambda s: (s.series_number is None, s.series_number, s.description),
    )
