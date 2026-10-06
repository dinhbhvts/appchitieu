"""Tests for the digital photo frame album (khung ảnh kỹ thuật số)."""

import io

from PIL import Image


def _jpeg(w=3000, h=2000, color=(200, 100, 50), exif_orientation=None) -> bytes:
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    if exif_orientation:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        img.save(buf, format="JPEG", exif=exif)
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue()


def _png_rgba() -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (400, 300), (0, 0, 255, 128)).save(buf, format="PNG")
    return buf.getvalue()


def test_upload_downscales_and_lists_without_binary(client):
    r = client.post("/album-photos", files={"file": ("dalat.jpg", _jpeg(), "image/jpeg")},
                    data={"caption": "  Đà Lạt 2026  "})
    assert r.status_code == 201, r.text
    p = r.json()
    assert (p["width"], p["height"]) == (1280, 853)   # longest side capped at 1280
    assert p["caption"] == "Đà Lạt 2026"
    assert "image_data" not in p

    listed = client.get("/album-photos").json()
    assert [x["id"] for x in listed] == [p["id"]]

    full = client.get(f"/album-photos/{p['id']}/image")
    assert full.status_code == 200
    assert full.headers["content-type"] == "image/jpeg"
    assert "immutable" in full.headers["cache-control"]
    thumb = client.get(f"/album-photos/{p['id']}/image", params={"size": "thumb"})
    t = Image.open(io.BytesIO(thumb.content))
    assert max(t.size) == 320
    assert len(thumb.content) < len(full.content)


def test_exif_rotation_applied(client):
    # Orientation 6 = rotate 90° -> a landscape-encoded photo becomes portrait.
    r = client.post("/album-photos",
                    files={"file": ("p.jpg", _jpeg(2000, 1000, exif_orientation=6), "image/jpeg")})
    p = r.json()
    assert p["height"] > p["width"]


def test_png_with_transparency_accepted(client):
    r = client.post("/album-photos", files={"file": ("x.png", _png_rgba(), "image/png")})
    assert r.status_code == 201
    assert (r.json()["width"], r.json()["height"]) == (400, 300)  # small image not upscaled


def test_non_image_rejected(client):
    r = client.post("/album-photos", files={"file": ("a.pdf", b"%PDF-1.4 not an image", "application/pdf")})
    assert r.status_code == 400
    assert "Không đọc được file ảnh" in r.json()["detail"]


def test_caption_update_and_soft_delete(client):
    pid = client.post("/album-photos", files={"file": ("a.jpg", _jpeg(800, 600), "image/jpeg")}).json()["id"]
    upd = client.patch(f"/album-photos/{pid}", json={"caption": "Sinh nhật Bông"})
    assert upd.json()["caption"] == "Sinh nhật Bông"
    assert client.delete(f"/album-photos/{pid}").status_code == 200
    assert client.get("/album-photos").json() == []
    assert client.get(f"/album-photos/{pid}/image").status_code == 404
