import { test, expect } from '@playwright/test';

test.describe('set app', () => {
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
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    // Mock history
    await page.route('**/workouts', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    // Mock routines
    await page.route('**/routines', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      });
    });

    await page.goto('/');
    // Login
    await page.getByLabel('Username').fill('testuser');
    await page.getByRole('button', { name: 'Mock Login' }).click();
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
