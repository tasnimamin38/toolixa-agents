"""Provider factory helpers."""

from toolixa_core.providers.base import ProviderError, ProviderRegistry


def create_provider(registry: ProviderRegistry, name: str, **configuration: object) -> object:
    """Instantiate only the explicitly selected registered provider."""
    factory = registry.get_factory(name)
    if not callable(factory):
        raise ProviderError(f"provider factory is invalid: {name}")
    try:
        return factory(**configuration)
    except Exception as exc:
        raise ProviderError(f"provider initialization failed: {name}") from exc
