// This project was developed with assistance from AI tools.

import { test, expect } from "@playwright/test";
import { BorrowerDashboardPage } from "../../pages/borrower-dashboard.page";

test.describe("Borrower Dashboard Cards", () => {
    let dashboard: BorrowerDashboardPage;

    test.beforeEach(async ({ page }) => {
        dashboard = new BorrowerDashboardPage(page);
        await dashboard.goto();
    });

    test("should show status card with application number and stage", async ({ page }) => {
        // Either shows an active application heading or "No active application found"
        const appHeading = page.getByRole("heading", { name: /Application #/ });
        const noApp = page.getByText("No active application found");
        await expect(appHeading.or(noApp).first()).toBeVisible();
    });

    test("should show stage stepper with stage labels", async ({ page }) => {
        await expect(page.getByText(/Application #/)).toBeVisible({ timeout: 10_000 });

        // Stage stepper renders responsive labels (two spans per stage: mobile hidden, desktop visible)
        await expect(page.getByText("Inquiry").last()).toBeVisible();
        await expect(page.getByText("Closed").last()).toBeVisible();
    });

    test("should display documents card", async () => {
        await expect(
            dashboard.page.getByRole("heading", { name: "Documents" }),
        ).toBeVisible();
    });

    test("should display conditions card", async ({ page }) => {
        // Either conditions list or "No outstanding conditions" message
        const conditionsHeading = page.getByRole("heading", {
            name: "Underwriting Conditions",
        });
        await expect(conditionsHeading).toBeVisible();
    });

    test("should display disclosures card", async () => {
        await expect(
            dashboard.page.getByRole("heading", { name: "Disclosures" }),
        ).toBeVisible();
    });

    test("should display rate lock or pre-qualification card", async ({ page }) => {
        const rateLock = page.getByRole("heading", { name: "Rate Lock" });
        const prequal = page.getByRole("heading", { name: "Pre-Qualification" });
        await expect(rateLock.or(prequal).first()).toBeVisible();
    });

    test("should display application summary with loan details", async ({ page }) => {
        const summaryHeading = page.getByRole("heading", {
            name: "Application Summary",
        });
        await expect(summaryHeading).toBeVisible();
    });

    test("should show loan amount in summary card", async ({ page }) => {
        await expect(page.getByText(/Application #/)).toBeVisible({ timeout: 10_000 });

        // Summary card should display a formatted currency value (may have multiple: property value + loan amount)
        const summaryCard = page.getByRole("heading", { name: "Application Summary" }).locator("../..");
        await expect(summaryCard.getByText(/\$[\d,]+/).first()).toBeVisible();
    });

    // C-1 + W-1: Replace three-way OR assertion and waitForTimeout with a
    // deterministic Playwright-native assertion that waits for any valid state.
    test("should show document rows or empty message in documents card", async ({ page }) => {
        const docsHeading = page.getByRole("heading", { name: "Documents" });
        await expect(docsHeading).toBeVisible();

        // Documents card should show either document rows or an empty/missing message.
        // Use Playwright's built-in retry instead of a fixed timeout.
        const docsCard = docsHeading.locator("../..");
        await expect(
            docsCard.getByText(/No documents|Missing documents/).or(docsCard.locator(".divide-y > div").first()),
        ).toBeVisible({ timeout: 5_000 });
    });
});
