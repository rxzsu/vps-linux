import { test, expect } from "@playwright/test";
test("renders the site, navigation, documentation and release links", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page).toHaveTitle(/VPS Linux/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Your server.",
  );
  await expect(page.getByText("x86_64", { exact: true }).first()).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Download v0.1" }).first(),
  ).toHaveAttribute(
    "href",
    "https://github.com/rxzsu/vps-linux/releases/download/v0.1/vps-linux-v0.1-release.qcow2",
  );
  await expect(
    page.getByRole("link", { name: "SHA256 checksum" }),
  ).toHaveAttribute("href", /\.qcow2\.sha256$/);
  if (info.project.name === "mobile") {
    const menu = page.getByRole("button", { name: "Toggle navigation" });
    await menu.click();
    await expect(menu).toHaveAttribute("aria-expanded", "true");
    await page
      .getByRole("navigation")
      .getByRole("link", { name: "Documentation" })
      .click();
    await expect(menu).toHaveAttribute("aria-expanded", "false");
  }
  const summary = page
    .locator("summary")
    .filter({ hasText: "Download & verify" });
  await summary.click();
  await expect(page.getByText("sha256sum -c", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Copy command" }).first().focus();
  await expect(
    page.getByRole("button", { name: "Copy command" }).first(),
  ).toBeFocused();
  for (const width of info.project.name === "mobile"
    ? [320, 390, 640]
    : [768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
  if (info.project.name === "reduced-motion") {
    await expect(page.locator(".terminal-line")).toHaveCount(3);
    expect(
      await page
        .locator(".cursor")
        .evaluate((el) => getComputedStyle(el).animationName),
    ).toBe("none");
  }
  expect(errors).toEqual([]);
  await page.setViewportSize({
    width: info.project.name === "mobile" ? 390 : 1440,
    height: 1000,
  });
  await page.goto("/");
  for (const section of [
    "#features",
    "#architecture",
    "#download",
    "#documentation",
  ]) {
    await page.locator(section).scrollIntoViewIfNeeded();
    await page.waitForTimeout(600);
  }
  await page.locator(".feature").first().scrollIntoViewIfNeeded();
  await expect(page.locator(".feature").first()).toHaveCSS("opacity", "1");
  await page.locator(".layer").first().scrollIntoViewIfNeeded();
  await expect(page.locator(".layer").first()).toHaveCSS("opacity", "1");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(600);
  await page.screenshot({
    path: `test-results/${info.project.name}.png`,
    fullPage: true,
  });
});
