from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[2] / "dashboard"

pytestmark = pytest.mark.skipif(
    not (WEB_DIR / "index.html").is_file(), reason="dashboard/ web app not present"
)


def test_web_app_is_served_at_the_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Mentora" in r.text


def test_web_app_files_are_served(client):
    assert client.get("/app.js").status_code == 200
    assert client.get("/styles.css").status_code == 200


def test_api_routes_still_win_over_the_web_app(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    assert client.get("/auth/me").status_code == 401  # API answers, not the web app


def test_tutor_character_files_are_served(client):
    page = client.get("/").text
    assert "avatar.js" in page and "importmap" in page
    for path in ("/avatar.js", "/vendor/three/three.module.min.js", "/vendor/three/three.core.min.js",
                 "/vendor/three/addons/loaders/GLTFLoader.js", "/vendor/three-vrm/three-vrm.module.min.js",
                 "/models/tutor.vrm"):
        assert client.get(path).status_code == 200, path
