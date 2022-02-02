from setuptools import setup

setup(
    name="workmon",
    version="0.1",
    description="Work monitoring",
    author="Vladimir Kotal",
    author_email="vlada@kotalovi.cz",
    packages=["workmon"],
    install_requires=[
        "pyserial",
        "adafruit-circuitpython-us100",
        "prometheus-client",
        "PyP100",
        "requests",
    ],
    entry_points={"console_scripts": ["workmon = workmon.workmon:run_main"]},
    tests_require=[
        "pytest",
        "pytest-cov",
    ],
)
