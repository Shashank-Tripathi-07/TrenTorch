#!/usr/bin/env python
"""
TrenTorch Sandbox Integrity Tests
==================================
Run this to ensure the student learning sandbox is robust.
All core infrastructure must work perfectly so students can
focus on learning ML systems, not debugging framework issues.
"""

import importlib
import os
import sys

# Test modules to run
TEST_MODULES = ["test_conv_linear_dimensions", "test_transformer_reshaping"]


def run_sandbox_tests():
    """Run all sandbox integrity tests."""
    print("=" * 60)
    print("🧪 TRENTORCH SANDBOX INTEGRITY CHECK")
    print("=" * 60)
    print("\nEnsuring the learning environment is robust...\n")

    all_passed = True
    results = []

    for test_module in TEST_MODULES:
        try:
            # Import and run the test module
            print(f"Running {test_module}...")
            module = importlib.import_module(test_module)

            # Look for a main function or run tests directly.
            #
            # A prior "elif '__main__' in dir(module)" branch here was meant
            # to skip re-running a module that already executes its own
            # tests on import, but dir(module) lists attribute names, not
            # execution state -- a module only gets a literal "__main__"
            # entry in dir() if it defines a variable with that exact name,
            # which none of these test modules do. The branch was always
            # dead code and always fell through to the else below anyway,
            # so removing it changes nothing about actual behavior, just
            # removes the misleading dead branch.
            if hasattr(module, "main"):
                module.main()
            else:
                # Try to run all test functions
                test_funcs = [f for f in dir(module) if f.startswith("test_")]
                for func_name in test_funcs:
                    func = getattr(module, func_name)
                    func()

            results.append((test_module, True, "PASSED"))
            print(f"  ✅ {test_module}: PASSED\n")

        except Exception as e:
            results.append((test_module, False, str(e)))
            print(f"  ❌ {test_module}: FAILED")
            print(f"     Error: {e}\n")
            all_passed = False

    # Summary
    print("=" * 60)
    print("📊 SANDBOX TEST SUMMARY")
    print("=" * 60)

    for module, passed, status in results:
        icon = "✅" if passed else "❌"
        print(f"{icon} {module}: {status}")

    if all_passed:
        print("\n🎉 SANDBOX IS ROBUST!")
        print("Students can focus on learning ML systems.")
        return 0
    else:
        print("\n⚠️  SANDBOX NEEDS ATTENTION")
        print("Some infrastructure tests failed.")
        print("Students might encounter framework issues.")
        return 1


if __name__ == "__main__":
    # Add the test directory to path
    test_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, test_dir)

    # Run tests
    exit_code = run_sandbox_tests()
    sys.exit(exit_code)
