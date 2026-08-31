"""
MC/DC coverage for _parse_pytest_output()'s per-line decision.

The decision that gates whether a line of captured pytest -v output is
treated as a test result at all is:

    "::" in line and ("PASSED" in line or "FAILED" in line)

three independent conditions (call them X, Y, Z). This decides what a
student is actually told passed or failed after `tren module test`, and
had no dedicated test at all before this: the only coverage was indirect,
through fixtures that happen to produce output matching the common case.

Four cases give real MC/DC: each condition's independent effect on the
decision is shown by a pair of cases differing only in that condition.
"""

from platforms.cli.processes.module_workflow.test_runner import _parse_pytest_output


def test_double_colon_and_passed_is_counted():
    """X=True, Y=True, Z=False -> counted, passed=True."""
    stdout = "tests/01_tensor/test_shapes.py::TestTensor::test_reshape PASSED"
    result = _parse_pytest_output(stdout, "")

    assert len(result) == 1
    assert result[0]["passed"] is True


def test_no_double_colon_is_not_counted():
    """X=False, Y=True, Z=False -> not counted. Paired with the test above:
    only X differs, isolating X's effect."""
    stdout = "some unrelated log line mentioning PASSED but no path separator"
    result = _parse_pytest_output(stdout, "")

    assert result == []


def test_double_colon_without_status_word_is_not_counted():
    """X=True, Y=False, Z=False -> not counted. Paired with the first test:
    only Y differs (True -> False), X held True, isolating Y's effect."""
    stdout = "tests/01_tensor/test_shapes.py::TestTensor::test_reshape COLLECTED"
    result = _parse_pytest_output(stdout, "")

    assert result == []


def test_double_colon_and_failed_is_counted():
    """X=True, Y=False, Z=True -> counted, passed=False. Paired with the
    previous test: only Z differs (False -> True), isolating Z's effect."""
    stdout = "tests/01_tensor/test_shapes.py::TestTensor::test_reshape FAILED"
    result = _parse_pytest_output(stdout, "")

    assert len(result) == 1
    assert result[0]["passed"] is False


def test_duplicate_test_paths_are_deduplicated():
    """Not part of the MC/DC set above, but a real behavior of the same
    function worth locking down while adding its first test: a repeated
    test_path (pytest sometimes echoes a line twice, e.g. with -rA summary
    output) should only be counted once."""
    stdout = (
        "tests/01_tensor/test_shapes.py::TestTensor::test_reshape PASSED\n"
        "tests/01_tensor/test_shapes.py::TestTensor::test_reshape PASSED\n"
    )
    result = _parse_pytest_output(stdout, "")

    assert len(result) == 1
