"""Curve dictionary (ADR-003 E4): raw LAS mnemonics → standard curves used by the lithology model.

One rock property is recorded under many mnemonics (GR, G/R, GRGC…). Rules are regular expressions on the upper-cased
mnemonic, checked in order; the first match wins. Unmatched curves stay unmapped and are counted in the inventory.
Mud-log gas curves (C1–C5, TG) are recognised explicitly so that, for example, C1 is never taken as a caliper.
"""

from __future__ import annotations

import re

RULES: list[tuple[str, str]] = [
    ("DEPTH", r"^(DEPT|DEPTH|MD|TDEP)$"),
    ("GAS", r"^(C[1-5]|IC4|NC4|IC5|NC5|C4/C5|TG|TGAS|TOTAL_?GAS|GAS)$"),
    ("GR", r"^(GR|G/R|SGR|CGR|GRC|GRGC|GRD|GRN|GRS|GRR|GRTO|GR_EDTC|GRAM|ECGR|HGR|GAM|GAMMA|GRCFM)(\[\d+\])?$"),
    ("RHOB", r"^(RHOB|RHOZ|ZDEN|DEN|DENS|RHO8|ZDNC|DENC|RHOC|BDEN|RHOM|DRHB|RHO|DEN\(.*\)|RHOB.+)$"),
    ("DRHO", r"^(DRHO|ZCOR|DCOR|CORR|DRH)$"),
    ("NPHI", r"^(NPHI|NPOR|TNPH|CNC|CNCF|CNPOR|NPHS|NPLS|NPSS|NPDL|PHIN|NEU|NEUT|CNL|NPRL|CN|CNS|CNSS|NPHL|DPHN|CNLS|CNDL|CNPS|POR\(NEU\)|NPHI.+|NPOR.+)$"),
    ("DPHI", r"^(DPHI|DPOR|DPHZ|PHID|DPHS|DPLS|DPRL|DPSS|DPHL|POR\(DEN\)|DPOR.+)$"),
    ("PEF", r"^(PE|PEF|PEFZ|PEFL|PDPE|PEDN)$"),
    ("DTC", r"^(DT|DTC|DTCO|AC|DT4P|DTL|DT24|SON|SONIC|DELT|DTLN|DTLF)$"),
    ("COND_DEEP", r"^(CILD|CIL|COND\(DI\)|CDI|CILD1)$"),
    ("RDEP", r"^(RT|RD|RDEP|ILD|RILD|LLD|RLLD|RLA5|AT90|AHT90|M2R9|HDRS|RES_DEEP|RDEEP|AIT90|HLLD|DIL|RILD1|ILD1|RES\(DI\)|RES\(DG\)|RLL4)$"),
    ("RMED", r"^(RM|RMED|ILM|RILM|LLS|RLLS|RLA3|AT30|AHT30|M2R3|HMRS|RES_MED|IMPH|RES\(MI\))$"),
    ("RSHA", r"^(RS|RSHA|SFL|SFLU|SFLA|MSFL|RXO|RLA1|AT10|AHT10|M2R1|LL8|SN|RSFL|RLL3|RLL1)$"),
    ("CALI", r"^(CALI|CAL|HCAL|CALX|CALY|LCAL|CALS|CAL1|CAL2|CALD|CLDC|CALN|CALIPER|MCAL|MELCAL)$"),
    ("DCAL", r"^(DCAL)$"),
    ("SP", r"^(SP|SPR|SPBR|SSP|SPCG)$"),
    ("BS", r"^(BS|BIT|BITSIZE)$"),
    ("PHI_OTHER", r"^(SPHI|PHIS|SPOR)$"),
    ("MICRO", r"^(MI|MN|MINV|MNOR|MNRL|MEL\d+|RXORT|RXRT|MLL|MSFL\d*)$"),
    ("TOOL_QC", r"^(CCL|LTEN|TENS|TEN|LSPD|SPD|TEMP|DEL ?TEMP|ITT|AVTX|BVTX|ABHV|TBHV|CGXT|COMP|DGA|FEFE|HTEN|MTEMP|SPEED)$"),
]
LITHOLOGY = {"GR", "RHOB", "DRHO", "NPHI", "DPHI", "PEF", "DTC", "COND_DEEP", "RDEP", "RMED", "RSHA", "CALI", "SP", "BS", "PHI_OTHER", "DCAL"}
_RULES = [(std, re.compile(rx)) for std, rx in RULES]
CORE = ["GR", "RHOB", "NPHI", "DTC", "RDEP"]          # the logs the FORCE model leans on most


def standard_name(mnemonic: str) -> str | None:
    m = mnemonic.strip().upper().replace(" ", "")
    for std, rx in _RULES:
        if rx.match(m):
            return std
    return None
