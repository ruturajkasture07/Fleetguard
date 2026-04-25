"""Minimal compatibility shim for libraries expecting pkg_resources.

Razorpay's Python SDK calls pkg_resources.require("razorpay")[0].version to build
its user-agent string. Python 3.14 environments may not expose pkg_resources by
default, so we provide a tiny local fallback with the required interface.
"""

from importlib import metadata


class _Dist:
    def __init__(self, version: str) -> None:
        self.version = version


def require(distribution_name: str):
    try:
        return [_Dist(metadata.version(distribution_name))]
    except metadata.PackageNotFoundError as exc:
        raise DistributionNotFound(str(exc)) from exc


class DistributionNotFound(Exception):
    pass
