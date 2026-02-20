from api.app.main import app

def test_chunks_route(client):
    r = client.get("/chunks/number_of_chunks")
    assert r.status_code == 200
    data = r.json()
    assert "number_of_chunks" in data
    assert isinstance(data["number_of_chunks"], int)
    # There should be no chunks initially
    assert data["number_of_chunks"] == 0

    #response = client.get(
    #    f"/chunks/{chunk_id}"
    #)

    #assert response.status_code == 200
    #data = response.json()
    #assert "chunk_id" in data
