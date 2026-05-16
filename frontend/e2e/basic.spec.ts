import { test, expect } from '@playwright/test';

test.describe('set app', () => {
  test('should show login page and allow login', async ({ page }) => {
    await page.goto('/');
    
    // Check for title
    await expect(page.locator('h1')).toHaveText('set');
    
    // Login
    await page.fill('input[placeholder="Enter your username"]', 'testuser');
    await page.click('button:has-text("Login")');
    
    // Check if logged in (user name should appear in header)
    await expect(page.locator('header')).toContainText('testuser');
  });

  test('should allow adding an exercise', async ({ page }) => {
    await page.goto('/');
    await page.fill('input[placeholder="Enter your username"]', 'testuser');
    await page.click('button:has-text("Login")');

    // Click add exercise
    await page.click('button:has-text("+ Add Exercise")');
    
    // Fill exercise name
    await page.fill('input[placeholder="Search exercise..."]', 'Bench Press');
    await page.click('button:has-text("Add")');
    
    // Check if exercise added
    await expect(page.locator('.exercise-row')).toContainText('Bench Press');
  });
});
