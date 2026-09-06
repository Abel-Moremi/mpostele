import sys
import unittest

from pipeline.benchmark import BenchmarkResult, _descendants, run_benchmark


class BenchmarkTests(unittest.TestCase):
    def test_descendants_follows_multiple_generations(self):
        parents = {11: 10, 12: 11, 13: 99, 14: 12}
        self.assertEqual(_descendants(10, parents), {10, 11, 12, 14})

    def test_run_benchmark_reports_exit_and_peak_sample(self):
        samples = iter([1024, 4096, 2048, 2048])

        def sampler(_pid):
            return next(samples, 2048)

        result = run_benchmark(
            [sys.executable, "-c", "import time; time.sleep(0.06)"],
            sample_interval=0.01,
            sampler=sampler,
        )
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.peak_tree_rss_bytes, 4096)
        self.assertGreater(result.samples, 0)
        self.assertGreater(result.elapsed_seconds, 0)

    def test_elapsed_time_does_not_wait_out_the_sampling_interval(self):
        result = run_benchmark(
            [sys.executable, "-c", "pass"],
            sample_interval=0.5,
            sampler=lambda _pid: None,
        )
        self.assertLess(result.elapsed_seconds, 0.4)

    def test_report_adds_mebibyte_value(self):
        result = BenchmarkResult(("demo",), 1.0, 2 * 1024 * 1024, 3, 0)
        report = result.to_dict()
        self.assertEqual(report["peak_tree_rss_mib"], 2.0)
        self.assertEqual(report["command"], ["demo"])

    def test_rejects_invalid_arguments(self):
        with self.assertRaises(ValueError):
            run_benchmark([])
        with self.assertRaises(ValueError):
            run_benchmark([sys.executable], sample_interval=0)


if __name__ == "__main__":
    unittest.main()
