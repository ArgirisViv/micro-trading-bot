"""Provider entrypoint loaded lazily; offline validators never load credentials."""

def get_live_data(*args, **kwargs):
    from .live_data_fetch import get_live_data as fetch
    return fetch(*args, **kwargs)

__all__ = ['get_live_data']
