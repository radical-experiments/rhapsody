# HPPSS W1: video-sized run (4 cases/batch, 4 batches) without editing the example
import asyncio
import importlib.util
import pathlib

spec = importlib.util.spec_from_file_location(
    "driver_staged", pathlib.Path(__file__).with_name("driver-staged.py"))
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)

if __name__ == "__main__":
    asyncio.run(driver.main(ensemble_size=4, max_iterations=4))
