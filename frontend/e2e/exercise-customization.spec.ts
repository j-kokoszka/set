import { test, expect } from '@playwright/test';

test.describe('Exercise Library Expansion & Customization', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the backend exercises endpoint
    await page.route('**/exercises', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'Bench_Press', name: 'Bench Press', category: 'strength', primaryMuscles: ['chest'] }
        ])
      });
    });

    // Mock custom exercises
    await page.route('**/exercises/custom', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([])
        });
      } else if (route.request().method() === 'POST') {
        const body = JSON.parse(route.request().postData() || '{}');
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ...body, id: 'custom-123' })
        });
      }
    });

    // Mock external search
    await page.route('**/exercises/search?q=Low%20Row', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'ext-1', name: 'External Low Row', category: 'strength', primaryMuscles: [], is_external: true }
        ])
      });
    });

    await page.goto('/');
    // Login using Mock Login as seen in basic.spec.ts
    await page.getByLabel('Username').fill('testuser');
    await page.getByRole('button', { name: 'Mock Login' }).click();
    await expect(page.locator('header')).toContainText('testuser');
  });

  test('should be able to create and use a custom exercise', async ({ page }) => {
    // 1. Open Add Exercise modal
    await page.getByRole('button', { name: '+ Add Exercise' }).click();
    
    // 2. Search for something non-existent to trigger custom flow
    const searchInput = page.getByPlaceholder('Search exercise...');
    await searchInput.fill('Super Ultra Squat');
    
    // 3. Click "Create Custom"
    await page.click('text=➕ Create Custom: "Super Ultra Squat"');
    
    // 4. Fill custom exercise form
    await expect(page.locator('text=Create Custom Exercise')).toBeVisible();
    await page.fill('input[placeholder="e.g. lats"]', 'quads');
    await page.click('button:has-text("Save & Add")');
    
    // 5. Verify it was added to the workout
    await expect(page.locator('.exercise-row')).toContainText('Super Ultra Squat');
  });

  test('should be able to search online database', async ({ page }) => {
    await page.getByRole('button', { name: '+ Add Exercise' }).click();
    
    const searchInput = page.getByPlaceholder('Search exercise...');
    await searchInput.fill('Low Row');
    
    // Click Search Online
    await page.click('text=🔍 Search "Low Row" online');
    
    // Wait for external results (labeled with [Online])
    await expect(page.locator('text=[Online]').first()).toBeVisible();
    await page.click('text=External Low Row');
    
    // Verify it was added
    await expect(page.locator('.exercise-row')).toContainText('External Low Row');
  });
});
