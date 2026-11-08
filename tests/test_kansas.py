"""ADR-005 §5: Kansas LAS preparation rules."""

import io
import zipfile

import numpy as np

from src.kansas import parse_data, read_entry, resample, standardise

LAS = b"""~VERSION INFORMATION
 VERS.   2.0 :   CWLS LOG ASCII STANDARD - VERSION 2.0
 WRAP.   NO  :   ONE LINE PER DEPTH STEP
~WELL INFORMATION
 STRT.FT  1000.0 :
 STOP.FT  1003.0 :
 STEP.FT     0.5 :
 NULL.   -999.25 :
 WELL.   TEST #1 :
~CURVE INFORMATION
 DEPT.FT        : Depth
 GR  .GAPI      : Gamma ray
 CNLS.PU        : Neutron porosity, limestone
 DPHI.PU        : Density porosity
 ILD .OHMM      : Deep induction
~A
1000.0  40.0  15.0  10.0  20.0
1000.5  42.0  16.0  11.0  21.0
1001.0  -999.25  17.0  12.0  22.0
1001.5  44.0  18.0  13.0  23.0
1003.0  46.0  20.0  15.0  25.0
"""


def test_units_density_from_porosity_and_nulls():
    h, df = parse_data(LAS)
    s = standardise(h, df)
    assert np.isclose(s.DEPTH_MD.iloc[0], 1000.0 * 0.3048)
    assert np.isclose(s.NPHI.iloc[0], 0.15)                       # percent → fraction
    assert np.isclose(s.RHOB.iloc[0], 2.71 - 1.71 * 0.10)          # density from density porosity
    assert np.isnan(s.GR.iloc[2]) and np.isclose(s.RDEP.iloc[0], 20.0)


def test_resample_grid_and_no_bridging_of_gaps():
    h, df = parse_data(LAS)
    r = resample(standardise(h, df))
    assert np.allclose(np.diff(r.DEPTH_MD), 0.1524, atol=1e-3)
    gap = (r.DEPTH_MD > 1001.6 * 0.3048) & (r.DEPTH_MD < 1002.9 * 0.3048)   # 1.5 ft (0.46 m) without samples
    assert r.loc[gap, "NPHI"].isna().all() and r.NPHI.notna().sum() > 0


def test_nested_zip_entry_is_read():
    inner = io.BytesIO(); zipfile.ZipFile(inner, "w").writestr("123.las", LAS)
    outer = io.BytesIO(); zf = zipfile.ZipFile(outer, "w"); zf.writestr("2014/123.zip", inner.getvalue()); zf.close()
    outer.seek(0)
    p = "/tmp/claude_test_outer.zip"; open(p, "wb").write(outer.getvalue())
    assert read_entry(p, "2014/123.zip/123.las").startswith(b"~VERSION")
