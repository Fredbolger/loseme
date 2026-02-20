from api.app.main import app

def test_search_route(client):
    search_query = "test"
    response = client.post(
        "/search",
        json={"query": search_query, "top_k": 3}
    )
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert hasattr(data["results"], "__iter__")  # Check if results is iterable
    

