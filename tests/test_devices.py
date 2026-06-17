"""
Tests for device tracking + pruning + thread-safety of the shared state.
"""
import time
import threading

import local_drop as L


def test_register_client_adds_node(app_module):
    L.register_client("10.0.0.5", "Mozilla/5.0 (iPhone)", "viewer")
    assert "10.0.0.5" in app_module.connected_clients
    node = app_module.connected_clients["10.0.0.5"]
    assert node["device"] == "mobile"
    assert node["role"] == "viewer"
    assert "joined" in node


def test_register_client_updates_last_seen(app_module):
    L.register_client("10.0.0.6", "desktop ua")
    first = app_module.connected_clients["10.0.0.6"]["last_seen"]
    time.sleep(0.01)
    L.register_client("10.0.0.6", "desktop ua")
    assert app_module.connected_clients["10.0.0.6"]["last_seen"] > first


def test_prune_stale_removes_old_clients(app_module):
    L.register_client("10.0.0.7", "desktop ua")
    # age it past the 12s timeout
    app_module.connected_clients["10.0.0.7"]["last_seen"] = time.time() - 60
    L.prune_stale()
    assert "10.0.0.7" not in app_module.connected_clients


def test_prune_stale_keeps_recent_clients(app_module):
    L.register_client("10.0.0.8", "desktop ua")
    L.prune_stale()
    assert "10.0.0.8" in app_module.connected_clients


def test_prune_stale_custom_timeout(app_module):
    L.register_client("10.0.0.9", "desktop ua")
    app_module.connected_clients["10.0.0.9"]["last_seen"] = time.time() - 5
    L.prune_stale(timeout=10)   # 5s old < 10s -> kept
    assert "10.0.0.9" in app_module.connected_clients


def test_prune_stale_custom_timeout_evicts(app_module):
    L.register_client("10.0.0.10", "desktop ua")
    app_module.connected_clients["10.0.0.10"]["last_seen"] = time.time() - 5
    L.prune_stale(timeout=3)    # 5s old > 3s -> evicted
    assert "10.0.0.10" not in app_module.connected_clients


# ── thread-safety ─────────────────────────────────────────────────────────────
def test_concurrent_registration_no_corruption(app_module):
    N = 50
    errors = []

    def worker(i):
        try:
            for _ in range(20):
                L.register_client(f"192.168.1.{i}", "desktop ua")
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(1, N + 1)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    # each IP registered exactly once (register only adds on first sight)
    assert len(app_module.connected_clients) == N
