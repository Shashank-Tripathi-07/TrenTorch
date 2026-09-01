"""Throwaway file to verify the autofix bot actually pushes a fix commit
that re-triggers CI. Deleted once verified. Deliberately has a lint issue
(unused import, bad spacing) for ruff --fix / ruff format to clean up."""

import os
import sys


def noop() -> None:
    x  =  1
    return x
