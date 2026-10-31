"""Turns the photographed sketches into flat 'scans': finds the paper, corrects the perspective to A4 landscape,
whitens the background and saves them to Sketches/scanned. Originals stay untouched in Sketches/original."""
from pathlib import Path
import cv2
import numpy as np

D = Path(__file__).resolve().parents[1] / "Sketches"
OUT = D / "scanned"
OUT.mkdir(exist_ok=True)
W, H = 2970, 2100   # A4 landscape, 10 px per mm


def order(pts):
    pts = pts.reshape(4, 2).astype("float32")
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.array([pts[s.argmin()], pts[d.argmin()], pts[s.argmax()], pts[d.argmax()]], dtype="float32")  # tl, tr, br, bl


def paper_corners(img):
    small = cv2.resize(img, None, fx=0.25, fy=0.25)
    gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (9, 9), 0)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)          # white paper vs dark table
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cnts, key=cv2.contourArea)
    peri = cv2.arcLength(c, True)
    for eps in (0.02, 0.03, 0.04, 0.05):
        approx = cv2.approxPolyDP(c, eps * peri, True)
        if len(approx) == 4:
            return order(approx) * 4, cv2.contourArea(c) / th.size
    rect = cv2.boxPoints(cv2.minAreaRect(c))
    return order(rect) * 4, cv2.contourArea(c) / th.size


def whiten(img):
    """Divide by the blurred background so the paper becomes white and the ink keeps its colour."""
    f = img.astype("float32")
    bg = cv2.GaussianBlur(f, (0, 0), 60)
    out = np.clip(f / np.maximum(bg, 1) * 245, 0, 255)
    return out.astype("uint8")


for name in ("sketch_part1", "sketch_part2", "v1_annotated", "sketch_p4"):
    img = cv2.imread(str(D / "original" / f"{name}.jpg"))
    src, share = paper_corners(img)
    M = cv2.getPerspectiveTransform(src, np.array([[0, 0], [W, 0], [W, H], [0, H]], dtype="float32"))
    flat = cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_CUBIC)
    flat = flat[25:H - 25, 25:W - 25]                 # trim the paper edge
    out = whiten(flat)
    if name != "v1_annotated":
        # pen-only pages: remove the faint show-through of the sheet underneath (light, low-saturation pixels -> white)
        hsv = cv2.cvtColor(out, cv2.COLOR_BGR2HSV)
        faint = (hsv[..., 2] > 222) & (hsv[..., 1] < 22)   # only the very faint grey; ink lines keep their edges
        out[faint] = 255
    cv2.imwrite(str(OUT / f"{name}.jpg"), out, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(name, "paper share of photo:", round(share, 2), "corners:", src.astype(int).tolist())
