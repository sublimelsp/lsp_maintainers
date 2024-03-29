import puppeteer from "puppeteer";
import fs from "fs"

// when the 19 April comes look at the TODOs:

// TODO_1 - Load real data: ./LSP-info-for-release.json
/** @type {{
 * name: string
 * current_tag: string
 * proposed_tag: string
 * pr: string
 * }[]} */
// const data = JSON.parse(fs.readFileSync('./LSP-info-for-release.json'));
const data = [
  {
    "name": "LSP-x",
    "current_tag": "v2.6.5",
    "proposed_tag": "v3.0.0",
    "pr": "https://github.com/predragnikolic/repro-st-unit-test-bug/pull/1"
  },
]

const wait = (n) => new Promise((resolve) => setTimeout(resolve, n));


async function main () {
  // Launch the browser and open a new blank page
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1024 });

  await page.goto(`https://github.com/login`);
  await page.waitForSelector("#login_field")
  await page.type("#login_field", "predragnikolic");
  await page.type("#password", "");
  await page.click(" input[type=submit]");

  await page.waitForSelector('a[data-test-selector="totp-sms-link"]')
  await page.click('a[data-test-selector="totp-sms-link"]');

  await page.waitForSelector("button[type=submit]")
  await page.click("button[type=submit]");

  await page.waitForSelector("#dashboard")

  // merge prs
  for (const lspPackage of data) {
    await page.goto(lspPackage.pr);

    // TODO_2  remove `return` to allow merging PRs.
    return

    // Click merge button
    await page.waitForSelector(".merge-box-button")
    await page.click(".merge-box-button");

    // Confirm merge
    await page.click(".js-merge-commit-button");

    // delete branch
    await page.waitForSelector(".post-merge-message")
    await page.click(".post-merge-message button");
  }

  await wait(1000)
  await browser.close();
}
main()
