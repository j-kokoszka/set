import { test, expect } from '@playwright/test';

test.describe('Exercise Library Expansion & Customization', () => {
  test.beforeEach(async ({ page }) => {
    // Navigating with a longer timeout and waiting for initial load
    await page.goto('/', { waitUntil: 'networkidle' });
    
    // Check if we are already logged in or need to log in
    const loginInput = page.locator('input[placeholder="Enter your name"]');
    if (await loginInput.isVisible()) {
        await loginInput.fill('Test User');
        await page.click('button:has-text("Login")');
    }
    
    await expect(page.locator('.workout-header')).toBeVisible({ timeout: 10000 });
  });

  test('should be able to create and use a custom exercise', async ({ page }) => {
    // 1. Open Add Exercise modal
    await page.click('button:has-text("Add Exercise")');
    
    // 2. Search for something non-existent to trigger custom flow
    const searchInput = page.locator('input[placeholder="Search exercise..."]').first();
    await searchInput.fill('Super Ultra Squat');
    
    // 3. Click "Create Custom"
    await page.click('text=➕ Create Custom: "Super Ultra Squat"');
    
    // 4. Fill custom exercise form
    await expect(page.locator('text=Create Custom Exercise')).toBeVisible();
    await page.fill('input[placeholder="e.g. lats"]', 'quads');
    await page.click('button:has-text("Save & Add")');
    
    // 5. Verify it was added to the workout
    await expect(page.locator('.exercise-title:has-text("Super Ultra Squat")')).toBeVisible();
  });

  test('should be able to search online database', async ({ page }) => {
    await page.click('button:has-text("Add Exercise")');
    
    const searchInput = page.locator('input[placeholder="Search exercise..."]').first();
    await searchInput.fill('Low Row');
    
    // Click Search Online
    await page.click('text=🔍 Search "Low Row" online');
    
    // Wait for external results (labeled with [Online])
    // We expect at least one result containing "[Online]"
    await expect(page.locator('text=[Online]').first()).toBeVisible({ timeout: 15000 });
  });
});
