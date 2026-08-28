from playwright.sync_api import sync_playwright
import subprocess, time, os, signal, sys

srv = subprocess.Popen([sys.executable, "serve.py", "8124"],
                       cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
errs = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 1300})
        pg.add_init_script("""
          // minimal Leaflet stand-in: this sandbox cannot reach the CDN, so the
          // test exercises the game flow rather than the real map
          window.L = {
            map: (id) => ({ _h:{}, setView(){return this}, on(ev,fn){this._h[ev]=fn; window.__mapclick=fn; return this},
                            removeLayer(){}, fitBounds(){}, getZoom:()=>12, addLayer(){} }),
            tileLayer: () => ({ addTo(){ return this } }),
            marker: () => ({ addTo(){ return this } }),
            polyline: () => ({ addTo(){ return this } }),
            divIcon: (o) => o,
            latLngBounds: () => ({ pad(){ return this } })
          };
        """)
        pg.on("pageerror", lambda e: errs.append("PAGEERROR: " + str(e)))
        pg.on("console", lambda m: errs.append("CONSOLE " + m.type + ": " + m.text)
              if m.type == "error" and "tile" not in m.text and "ERR_" not in m.text else None)
        pg.goto("http://localhost:8124/", wait_until="networkidle")
        pg.wait_for_timeout(1500)
        print("round label:", pg.locator("#roundlab").inner_text())
        print("readout:", pg.locator("#readout").inner_text().replace("\n", " "))
        print("plate cap:", pg.locator("#platecap").inner_text())
        print("buildings loaded:", pg.evaluate("BUILDINGS.length"), "| pool:", pg.evaluate("POOL.length"))
        # place a pin, set a date, submit
        pg.evaluate("window.__mapclick({latlng:{lat:54.77,lng:-1.58}})")
        pg.wait_for_timeout(300)
        print("mapnote:", pg.locator("#mapnote").inner_text())
        rb = pg.locator("#ruler").bounding_box()
        pg.mouse.click(rb["x"] + rb["width"] * 0.72, rb["y"] + rb["height"] * 0.5)
        pg.wait_for_timeout(200)
        pg.click("#submit")
        pg.wait_for_timeout(800)
        print("reveal:", pg.locator("#revtitle").inner_text())
        print("scores:", pg.locator("#sdate").inner_text().replace("\n", "/"), "|",
              pg.locator("#splace").inner_text().replace("\n", "/"), "|",
              pg.locator("#sround").inner_text().replace("\n", "/"))
        pg.screenshot(path="app-shot.png", full_page=True)
        # play out the remaining rounds
        for _ in range(6):
            if pg.locator("#final").is_visible():
                break
            pg.click("#next"); pg.wait_for_timeout(400)
            if pg.locator("#final").is_visible():
                break
            pg.evaluate("window.__mapclick({latlng:{lat:53.4,lng:-1.5}})")
            pg.wait_for_timeout(200)
            pg.click("#submit"); pg.wait_for_timeout(500)
        print("final:", pg.locator("#totaltxt").inner_text().replace("\n", " "))
        pg.goto("http://localhost:8124/upload.html", wait_until="networkidle")
        pg.wait_for_timeout(800)
        print("uploader:", pg.locator("#count").inner_text(), "| rows:", pg.locator(".row").count())
        pg.screenshot(path="upload-shot.png", full_page=False)
        b.close()
finally:
    srv.send_signal(signal.SIGINT); srv.wait(timeout=5)
print("errors:", errs or "none")
