"""ADR-003 E3–E4: header parsing (LAS 2.0 and 1.2) and the curve dictionary."""

from src.curves import standard_name
from src.las_header import parse_header

LAS20 = b"""~VERSION INFORMATION
VERS. 2.0 : CWLS Log ASCII Standard - version 2.0
WRAP.  NO : One line per depth step
~WELL INFORMATION
STRT        .FT        500.0000 :START DEPTH
STOP        .FT       7053.0000 :STOP DEPTH
STEP        .FT          1.0000 :STEP
NULL        .         -999.2500 :NULL
API         .  15-015-23988-0100 :API NUMBER
LAT         .         37.884224 :LATITUDE
~CURVE INFORMATION
DEPTH    .FT           : Measured Depth
G/R      .   UNKNOWN   :
DEN(CDL) .G/C3         : Density
C1       .             : Methane
~A  DEPTH G/R
500 1 2
"""
LAS12 = b"""~V
VERS.   1.2:   CWLS LOG ASCII STANDARD
~W
STRT.FT   1200.0:
NULL.     -999.25:
WELL.     : SMITH 1
~C
DEPT.FT   : Depth
GR  .GAPI : Gamma
~A
"""


def test_las20_header():
    h = parse_header(LAS20)
    assert (h["version"], h["wrap"], h["null"], h["strt"], h["stop"], h["step"]) == ("2.0", "NO", -999.25, 500.0, 7053.0, 1.0)
    assert h["api"] == "15-015-23988-0100" and abs(h["lat"] - 37.884224) < 1e-9 and h["n_curves"] == 4


def test_las12_value_in_description():
    h = parse_header(LAS12)
    assert h["version"] == "1.2" and h["strt"] == 1200.0 and h["well"] == "SMITH 1" and h["n_curves"] == 2


def test_curve_dictionary():
    assert [standard_name(m) for m in ["G/R", "DEN(CDL)", "POR(NEU)", "RES(DI)", "CALIPER", "C1", "DCAL", "CCL"]] == \
        ["GR", "RHOB", "NPHI", "RDEP", "CALI", "GAS", "DCAL", "TOOL_QC"]
