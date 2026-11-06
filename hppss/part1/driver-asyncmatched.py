# HPPSS W1: async driver matched to the staged defaults (5 in flight, 1e-3), without editing the example
import asyncio
import importlib.util
import pathlib

spec = importlib.util.spec_from_file_location(
    "driver_async", pathlib.Path(__file__).with_name("driver-async.py"))
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)

if __name__ == "__main__":
    asyncio.run(driver.main(max_concurrent_cases=5, convergence=1e-3))
