#!/usr/bin/env python3
"""
Comprehensive test runner for the Order Lifecycle system.
Runs all tests and validates the 15-second constraint.
"""

import asyncio
import sys
import os
import time
import subprocess
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))


class TestRunner:
    """Run comprehensive tests for the Order Lifecycle system."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
    
    def run_command(self, command, description):
        """Run a command and capture results."""
        print(f"\n🧪 {description}")
        print("=" * 60)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                print(f"✅ {description} - PASSED")
                print(result.stdout)
                self.test_results[description] = "PASSED"
            else:
                print(f"❌ {description} - FAILED")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                self.test_results[description] = "FAILED"
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {description} - TIMEOUT")
            self.test_results[description] = "TIMEOUT"
        except Exception as e:
            print(f"💥 {description} - ERROR: {e}")
            self.test_results[description] = "ERROR"
    
    def run_unit_tests(self):
        """Run unit tests for business logic."""
        self.run_command(
            "python3 -m pytest tests/test_business_logic.py -v",
            "Unit Tests - Business Logic Functions"
        )
    
    def run_workflow_tests(self):
        """Run integration tests for workflows."""
        self.run_command(
            "python3 -m pytest tests/test_workflows.py -v",
            "Integration Tests - Workflow Execution"
        )
    
    def run_performance_tests(self):
        """Run performance tests."""
        self.run_command(
            "python3 -m pytest tests/test_performance.py -v",
            "Performance Tests - 15-Second Constraint"
        )
    
    def run_api_tests(self):
        """Run API tests."""
        self.run_command(
            "python3 test_phase5.py",
            "API Tests - Endpoint Functionality"
        )
    
    def run_system_tests(self):
        """Run system tests."""
        self.run_command(
            "python3 scripts/test_system.py",
            "System Tests - End-to-End Validation"
        )
    
    def run_all_tests(self):
        """Run all tests."""
        self.start_time = time.time()
        
        print("🚀 Starting Comprehensive Test Suite")
        print("=" * 60)
        print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all test suites
        self.run_unit_tests()
        self.run_workflow_tests()
        self.run_performance_tests()
        self.run_api_tests()
        self.run_system_tests()
        
        # Calculate total time
        end_time = time.time()
        total_time = end_time - self.start_time
        
        # Print summary
        self.print_summary(total_time)
    
    def print_summary(self, total_time):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results.values() if result == "PASSED")
        failed = sum(1 for result in self.test_results.values() if result == "FAILED")
        timeout = sum(1 for result in self.test_results.values() if result == "TIMEOUT")
        error = sum(1 for result in self.test_results.values() if result == "ERROR")
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏰ Timeout: {timeout}")
        print(f"💥 Error: {error}")
        print(f"⏱️  Total Time: {total_time:.2f} seconds")
        
        print("\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status_icon = {
                "PASSED": "✅",
                "FAILED": "❌",
                "TIMEOUT": "⏰",
                "ERROR": "💥"
            }.get(result, "❓")
            print(f"  {status_icon} {test_name}: {result}")
        
        # Overall result
        if failed == 0 and timeout == 0 and error == 0:
            print("\n🎉 ALL TESTS PASSED! System is ready for production.")
        else:
            print(f"\n⚠️  {failed + timeout + error} test(s) failed. Please review and fix issues.")
        
        print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Main test runner."""
    runner = TestRunner()
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "unit":
            runner.run_unit_tests()
        elif test_type == "workflow":
            runner.run_workflow_tests()
        elif test_type == "performance":
            runner.run_performance_tests()
        elif test_type == "api":
            runner.run_api_tests()
        elif test_type == "system":
            runner.run_system_tests()
        else:
            print("Usage: python3 run_tests.py [unit|workflow|performance|api|system|all]")
            sys.exit(1)
    else:
        # Run all tests by default
        runner.run_all_tests()


if __name__ == "__main__":
    main()
