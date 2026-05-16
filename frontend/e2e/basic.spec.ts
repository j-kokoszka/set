import { test, expect } from '@playwright/test';

test.describe('set app', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Login
    await page.getByLabel('Username').fill('testuser');
    await page.getByRole('button', { name: 'Login' }).click();
  });

  test('should allow login and show user in header', async ({ page }) => {
    // Check if logged in (user name should appear in header)
    await expect(page.locator('header')).toContainText('testuser');
  });

  test('should allow adding an exercise', async ({ page }) => {
    // Click add exercise
    await page.getByRole('button', { name: '+ Add Exercise' }).click();
    
    // Fill exercise name
    await page.getByPlaceholder('Search exercise...').fill('Bench Press');
    // Press Enter instead of clicking Add because the dropdown might overlap the button
    await page.keyboard.press('Enter');
    
    // Check if exercise added
    await expect(page.locator('.exercise-row')).toContainText('Bench Press');
  });
});
