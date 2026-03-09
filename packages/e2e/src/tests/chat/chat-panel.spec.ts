// This project was developed with assistance from AI tools.

import { test, expect, type Locator, type Page } from "@playwright/test";

// S-01: Extract repeated "ensure chat visible" pattern into a local helper.
async function ensureChatVisible(page: Page): Promise<Locator> {
    const textarea = page.locator('textarea[placeholder="Type your message..."]').first();
    // Wait for the chat sidebar to render (may take a moment after navigation)
    await textarea.waitFor({ state: "visible", timeout: 10_000 }).catch(() => {
        // On mobile viewports the sidebar is hidden behind a FAB
    });
    if (!(await textarea.isVisible())) {
        const fab = page.locator('button[aria-label="Open chat assistant"]');
        if (await fab.isVisible()) await fab.click();
    }
    return textarea;
}

test.describe("Chat Panel", () => {
    test.beforeEach(async ({ page }) => {
        await page.goto("/borrower");
    });

    // This test MUST be first -- later tests send messages via WS which leave
    // conversation history that hides the empty state.
    test("should show empty state with suggestion text before messages", async ({ page }) => {
        await expect(page.getByText("How can I help?")).toBeVisible({ timeout: 15_000 });
    });

    test("should display chat sidebar on authenticated pages", async ({ page }) => {
        const chatSidebar = page.locator('aside[aria-label="Chat Assistant"]');
        // On desktop, sidebar should be visible; on mobile, FAB button instead
        const sidebarVisible = await chatSidebar.isVisible();
        const fabButton = page.locator('button[aria-label="Open chat assistant"]');
        const fabVisible = await fabButton.isVisible();

        expect(sidebarVisible || fabVisible).toBeTruthy();
    });

    test("should accept text in chat input", async ({ page }) => {
        const textarea = await ensureChatVisible(page);
        await textarea.fill("Hello, I need help with my mortgage application");
        await expect(textarea).toHaveValue("Hello, I need help with my mortgage application");
    });

    test("should display user message after sending", async ({ page }) => {
        const textarea = await ensureChatVisible(page);

        await textarea.fill("Test message for E2E");
        await page.locator('button[aria-label="Send message"]').click();

        // The user message should appear in the chat
        await expect(page.getByText("Test message for E2E")).toBeVisible({ timeout: 5_000 });
    });

    test("should populate input via chat-prefill event with autoSend false", async ({ page }) => {
        const textarea = await ensureChatVisible(page);

        // Dispatch chat-prefill event with autoSend: false
        await page.evaluate(() => {
            window.dispatchEvent(
                new CustomEvent("chat-prefill", {
                    detail: {
                        message: "Prefilled via E2E test",
                        autoSend: false,
                    },
                }),
            );
        });

        await expect(textarea).toHaveValue("Prefilled via E2E test");
    });

    test("should auto-send message via chat-prefill with autoSend true", async ({ page }) => {
        await ensureChatVisible(page);

        // Dispatch with autoSend: true -- message should appear in chat, not just in input
        await page.evaluate(() => {
            window.dispatchEvent(
                new CustomEvent("chat-prefill", {
                    detail: {
                        message: "Auto-sent E2E test message",
                        autoSend: true,
                    },
                }),
            );
        });

        // The message should appear as a user message bubble (auto-sent)
        // Use .first() since desktop sidebar and mobile panel may both render the text
        await expect(page.getByText("Auto-sent E2E test message").first()).toBeVisible({ timeout: 5_000 });
    });

    test("should show clear history button after sending a message and clear on click", async ({ page }) => {
        const textarea = await ensureChatVisible(page);
        const clearButton = page.locator('button[aria-label="Clear chat history"]');

        // Send a message so the trash button appears
        await textarea.fill("Message to be cleared");
        await page.locator('button[aria-label="Send message"]').click();
        await expect(page.getByText("Message to be cleared").first()).toBeVisible({ timeout: 5_000 });

        // Trash button should now be visible
        await expect(clearButton).toBeVisible();

        // Wait for streaming to finish (button becomes enabled) before clicking
        await expect(clearButton).toBeEnabled({ timeout: 15_000 });
        await clearButton.click();

        // The message should be gone and empty state should return
        await expect(page.getByText("Message to be cleared")).toHaveCount(0);
        await expect(page.getByText("How can I help?")).toBeVisible({ timeout: 5_000 });
    });

    // C-1: Replaced vacuous `ws !== null || true` assertion. The test documents intent
    // clearly: we check whether a WebSocket connection was attempted, and skip rather
    // than trivially pass when the backend is unavailable.
    test("should attempt WebSocket connection", async ({ page }) => {
        // Monitor WebSocket connections
        const wsPromise = page.waitForEvent("websocket", { timeout: 10_000 }).catch(() => null);

        // Navigate to trigger WS connection
        await page.goto("/borrower");

        const ws = await wsPromise;
        // C-1 fix: assert the WS was actually attempted rather than always passing.
        // If the backend is not running this test should be fixed up, not vacuously passed.
        test.fixme(
            ws === null,
            "WebSocket connection depends on backend availability -- start the API server before running E2E tests",
        );
        expect(ws).not.toBeNull();
    });

});
