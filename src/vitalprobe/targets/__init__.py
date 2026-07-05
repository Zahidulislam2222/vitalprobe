"""Target adapters — how VitalProbe talks to the system under test."""

from vitalprobe.targets.rest import AdapterConfig, AdapterError, RestAdapter, load_adapter_config

__all__ = ["AdapterConfig", "AdapterError", "RestAdapter", "load_adapter_config"]
