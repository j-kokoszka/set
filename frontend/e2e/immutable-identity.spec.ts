import { test, expect } from '@playwright/test';

test.describe('Immutable Identity System', () => {
  test('should allow successful login and data fetching with email identity', async ({ page }) => {
    // 1. Mock the routines endpoint
    await page.route('**/routines', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    // 2. Login as 'user@example.com'
    await page.goto('/');
    await page.getByPlaceholder('Username').fill('user@example.com');
    await page.getByRole('button', { name: 'Mock Login' }).click();

    // 3. Verify user name appears (which confirms auth succeeded and backend mapped the ID)
    await expect(page.locator('header')).toContainText('user@example.com');

    // 4. Verify we are in the workout view
    await expect(page.locator('.workout-name-input')).toBeVisible();
  });
});
