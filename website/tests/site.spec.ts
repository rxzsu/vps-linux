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
    page.getByRole("link", { name: "Download v0.2" }).first(),
  ).toHaveAttribute(
    "href",
    "https://github.com/rxzsu/vps-linux/releases/download/v0.2/vps-linux-v0.2.qcow2",
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
  if (info.project.name === "reduced-motion") {
    for (const effect of [".aurora", ".mote", ".trace-flow", ".server-stack"]) {
      expect(
        await page
          .locator(effect)
          .first()
          .evaluate((el) => getComputedStyle(el).animationName),
      ).toBe("none");
    }
  }
  if (info.project.name === "desktop") {
    const card = page.locator(".feature").first();
    await card.scrollIntoViewIfNeeded();
    await card.hover();
    await expect(card).toHaveAttribute("data-lit", "");
    expect(
      await card.evaluate((el) => el.style.getPropertyValue("--pointer-x")),
    ).toMatch(/px$/);
    await page.locator(".section-intro").first().hover();
    await expect(card).not.toHaveAttribute("data-lit");
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

test("switches between Russian and English and preserves the choice", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/?lang=ru#documentation");
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await expect(page).toHaveTitle("VPS Linux — Твой сервер. Ничего лишнего.");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Твой сервер.",
  );
  await expect(
    page.getByRole("button", { name: "Русский", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator('meta[name="description"]')).toHaveAttribute(
    "content",
    /Лёгкий образ Debian/,
  );
  await expect(page.locator('meta[property="og:locale"]')).toHaveAttribute(
    "content",
    "ru_RU",
  );
  await expect(page.locator(".feature h3").first()).toHaveText(
    "Контейнеры — сразу.",
  );
  await page
    .locator("summary")
    .filter({ hasText: "Скачивание и проверка" })
    .click();
  await expect(page.getByText("sha256sum -c", { exact: false })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Скопировать команду" }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Скачать v0.2" }).first(),
  ).toHaveAttribute("href", /vps-linux-v0\.2\.qcow2$/);
  await expect(page.locator(".terminal-bottom")).toContainText(
    "Все системы готовы",
  );
  for (const width of [320, 390, 640, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      `Russian overflow at ${width}px`,
    ).toBeTruthy();
  }
  await page.setViewportSize({ width: 390, height: 844 });
  const menu = page.getByRole("button", { name: "Открыть или закрыть меню" });
  await menu.click();
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Возможности", exact: true })
    .click();
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  // Keyboard-accessible language controls remain available outside the mobile menu.
  const english = page.getByRole("button", { name: "English", exact: true });
  await english.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page).toHaveURL(/lang=en#features$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Your server.",
  );
  await expect(
    page
      .locator("summary")
      .filter({ hasText: "Download & verify" })
      .locator(".."),
  ).toHaveAttribute("open", "");
  await page.getByRole("button", { name: "Русский", exact: true }).click();
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  // An explicit shared language wins over a saved preference.
  await page.goto("/?lang=en");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator('meta[property="og:locale"]')).toHaveAttribute(
    "content",
    "en_US",
  );
  await page.goto("/?lang=ru");
  for (const section of [
    "#features",
    "#architecture",
    "#download",
    "#documentation",
  ]) {
    await page.locator(section).scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  await page.screenshot({
    path: `test-results/${info.project.name}-ru.png`,
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("uses browser Russian and works when local storage is blocked", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "language", { get: () => "ru-RU" });
    Object.defineProperty(Storage.prototype, "getItem", {
      value: () => {
        throw new DOMException("Blocked", "SecurityError");
      },
    });
    Object.defineProperty(Storage.prototype, "setItem", {
      value: () => {
        throw new DOMException("Blocked", "SecurityError");
      },
    });
  });
  await page.goto("/?lang=invalid");
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Your server.",
  );
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
});
