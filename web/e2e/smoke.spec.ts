import { expect, test } from "@playwright/test";

test.describe.configure({ mode: "serial" });

test("smoke: home → block → tx → address → search", async ({ page }) => {
  // 1. Home shows tip height and ≥1 block row
  await page.goto("/");
  await expect(page.getByTestId("dashboard")).toBeVisible();
  const tip = page.getByTestId("tip-height");
  await expect(tip).toBeVisible();
  const tipText = (await tip.innerText()).trim();
  expect(Number(tipText)).toBeGreaterThanOrEqual(1);

  const blockRows = page.getByTestId("block-row");
  await expect(blockRows.first()).toBeVisible();
  const firstHeight = await blockRows.first().getAttribute("data-height");
  expect(firstHeight).toBeTruthy();

  // 2. Click block → block page renders hash
  await blockRows.first().locator("a").first().click();
  await expect(page.getByTestId("block-page")).toBeVisible();
  await expect(page.getByTestId("block-hash")).toBeVisible();
  const hashText = await page.getByTestId("block-hash").innerText();
  expect(hashText.length).toBeGreaterThan(8);

  // 3. Click a txid → tx page renders vin/vout
  const txRow = page.getByTestId("block-tx-row").first();
  await expect(txRow).toBeVisible();
  await txRow.locator("a").first().click();
  await expect(page.getByTestId("tx-page")).toBeVisible();
  await expect(page.getByTestId("tx-vin-vout")).toBeVisible();
  await expect(page.getByTestId("tx-vin").first()).toBeVisible();
  await expect(page.getByTestId("tx-vout").first()).toBeVisible();

  // 4. Navigate to an address from a vout (prefer linked address)
  const addrLink = page
    .getByTestId("tx-vout")
    .locator('a[href*="/address/"]')
    .first();
  const hasAddr = (await addrLink.count()) > 0;
  if (hasAddr) {
    await addrLink.click();
    await expect(page.getByTestId("address-page")).toBeVisible();
    await expect(page.getByTestId("address-balance")).toBeVisible();
  } else {
    // Coinbase-only / no address: use API to find a known address from tip coinbase.
    const tipRes = await page.request.get("/api/v1/regtest/tip");
    expect(tipRes.ok()).toBeTruthy();
    const tipBody = (await tipRes.json()) as { height: number; hash: string };
    const blockRes = await page.request.get(
      `/api/v1/regtest/block/${tipBody.height}/txs`,
    );
    expect(blockRes.ok()).toBeTruthy();
    const txs = (await blockRes.json()) as { txs: { txid: string }[] };
    const txRes = await page.request.get(
      `/api/v1/regtest/tx/${txs.txs[0]!.txid}`,
    );
    const tx = (await txRes.json()) as {
      vout: { scriptPubKey?: { address?: string; addresses?: string[] } }[];
    };
    let addr: string | undefined;
    for (const v of tx.vout) {
      addr =
        v.scriptPubKey?.address ??
        v.scriptPubKey?.addresses?.[0] ??
        undefined;
      if (addr) {
        break;
      }
    }
    expect(addr).toBeTruthy();
    await page.goto(`/address/${encodeURIComponent(addr!)}`);
    await expect(page.getByTestId("address-page")).toBeVisible();
    await expect(page.getByTestId("address-balance")).toBeVisible();
  }

  // 5. Search a block height → lands on block page
  await page.goto("/");
  await expect(page.getByTestId("dashboard")).toBeVisible();
  const height = tipText;
  await page.getByLabel("Search block, transaction, or address").fill(height);
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page).toHaveURL(new RegExp(`/block/${height}`));
  await expect(page.getByTestId("block-page")).toBeVisible();
  await expect(page.getByRole("heading", { name: `Block ${height}` })).toBeVisible();
});
