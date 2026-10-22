import os
from contextlib import contextmanager
from fastapi import HTTPException
from cassandra import DriverException
from cassandra.cluster import Cluster
from cassandra.io.asyncorereactor import AsyncoreConnection


@contextmanager
def session():
    cluster = None
    try:
        # Explicit portable reactor; pyasyncore supplies it on Python >= 3.12.
        cluster = Cluster([os.getenv('CASSANDRA_HOST', '127.0.0.1')],
                          connection_class=AsyncoreConnection, connect_timeout=5)
        connection = cluster.connect('pulsefit')
        connection.default_timeout = 5
        yield connection
    except (DriverException, OSError) as exc:
        raise HTTPException(503, 'Cassandra unavailable or schema missing. Check setup and .env.') from exc
    finally:
        if cluster is not None:
            cluster.shutdown()
