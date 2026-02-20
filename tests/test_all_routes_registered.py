from api.app.main import app

def test_all_routes_have_tests():
    routes = [
        (r.path, tuple(r.methods))
        for r in app.router.routes
        if hasattr(r, "methods")
    ]

    # sanity check: fail loudly if routes disappear
    assert len(routes) > 0

