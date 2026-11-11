// Real-browser tooltip check of docs/index.html (rules R10, R12, R17) in three modes: desktop light, dark, phone 400 px.
// Every chart (svg.plot): hovering a mark shows its tooltip inside the chart box, keyboard focus shows it too, and it
// hides on leave; no tooltip on load; collapsed sections closed on load; the what-if dial and well picker update the
// page; no sideways scroll; no JS errors; collapsed page height reported in screens (R12: about 7 or fewer).
// Run: make hover-test   (needs Node + Google Chrome)
const puppeteer = require("puppeteer-core");
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const [file, outDir] = process.argv.slice(2);
  const b = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", args: (process.env.CHROME_ARGS || "").split(" ").filter(Boolean), headless: "new" });
  const modes = [["desktop-light", 1280, 900, "light"], ["desktop-dark", 1280, 900, "dark"], ["phone-400", 400, 860, "light"]];
  let fails = 0, checks = 0;
  const ok = (cond, msg) => { checks++; if (!cond) { fails++; console.log("FAIL", msg); } };
  for (const [mode, W, H, scheme] of modes) {
    const page = await b.newPage(); await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
    await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: scheme }]);
    const errs = []; page.on("pageerror", (e) => errs.push(e.message));
    await page.goto("file://" + file, { waitUntil: "networkidle0" });
    ok(await page.$$eval(".tip", (ts) => ts.every((t) => getComputedStyle(t).display === "none")), `${mode}: no tooltip on load`);
    ok(await page.$$eval("details.more", (ds) => ds.length > 0 && ds.every((d) => !d.open)), `${mode}: collapsed sections closed on load`);
    const screens = await page.evaluate(() => document.documentElement.scrollHeight / innerHeight);
    if (mode === "desktop-light") { console.log(`collapsed page: ${screens.toFixed(1)} screens`); ok(screens <= 7.5, `${mode}: collapsed page ≲ 7 screens (${screens.toFixed(1)})`); }
    await page.$$eval("details", (ds) => ds.forEach((d) => (d.open = true)));
    ok(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)), `${mode}: no sideways scroll`);
    const ids = await page.$$eval("svg.plot", (ss) => ss.map((s) => s.id));
    ok(ids.length >= 6, `${mode}: ${ids.length} charts`);
    for (const id of ids) {
      const mark = await page.$(`#${id} [data-k]`);
      ok(!!mark, `${mode} ${id}: has hoverable marks`); if (!mark) continue;
      await mark.scrollIntoView(); await wait(150);
      const bb = await mark.boundingBox(); await page.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2); await wait(80);
      const res = await page.evaluate((id) => { const w = document.getElementById(id).closest('.chart'), t = w.querySelector(":scope > .tip");
        if (getComputedStyle(t).display === "none") return null; const r = t.getBoundingClientRect(), b = w.getBoundingClientRect();
        return { inside: r.left >= b.left - 1 && r.right <= b.right + 1 && r.top >= b.top - 1 && r.bottom <= b.bottom + 1, text: t.textContent.trim().slice(0, 60) }; }, id);
      ok(res && res.inside && res.text.length > 5, `${mode} ${id}: tooltip on hover inside its chart (${res ? res.text : "none"})`);
      if (res) { const wrap = await page.evaluateHandle((id) => document.getElementById(id).closest('.chart'), id); await wrap.asElement().screenshot({ path: `${outDir}/${mode}_${id}.png` }); }
      await page.mouse.move(1, 1); await wait(60);
      ok(await page.evaluate((id) => getComputedStyle(document.getElementById(id).closest('.chart').querySelector(":scope > .tip")).display === "none", id), `${mode} ${id}: tooltip hides on leave`);
      const focusable = await page.$(`#${id} [data-k][tabindex="0"]`);
      if (focusable) { await focusable.evaluate((el) => el.focus()); await wait(60);
        ok(await page.evaluate((id) => getComputedStyle(document.getElementById(id).closest('.chart').querySelector(":scope > .tip")).display !== "none", id), `${mode} ${id}: tooltip on keyboard focus`);
        await page.evaluate(() => document.activeElement.blur()); }
    }
    const before = await page.$eval("#whatif", (e) => e.textContent);
    await page.$eval("#conf", (s) => { s.value = 2; s.dispatchEvent(new Event("input")); });
    ok((await page.$eval("#whatif", (e) => e.textContent)) !== before, `${mode}: what-if dial updates the numbers`);
    const c0 = await page.$eval("#col-score", (e) => e.textContent);
    await page.$eval("#well-pick", (s) => { s.selectedIndex = (s.selectedIndex + 1) % s.options.length; s.dispatchEvent(new Event("change")); });
    ok((await page.$eval("#col-score", (e) => e.textContent)) !== c0, `${mode}: well picker redraws the column`);
    const colors = await page.evaluate(() => { const s = getComputedStyle(document.documentElement); return ["--bg", "--fg", "--accent", "--surface", "--l10"].every((v) => s.getPropertyValue(v).trim()); });
    ok(colors, `${mode}: colour tokens resolve`);
    ok(errs.length === 0, `${mode}: no JS errors ${errs.join("; ")}`);
    await page.close();
  }
  console.log(`${checks - fails}/${checks} results-page checks pass`);
  await b.close();
  process.exit(fails ? 1 : 0);
})();
