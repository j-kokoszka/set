import { test, expect } from '@playwright/test';

test.describe('Exercise Reordering', () => {
  test.beforeEach(async ({ page }) => {
    // Global mocks
    await page.route('**/exercises', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/workouts', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/routines', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    
    // Login
    await page.goto('/');
    await page.getByPlaceholder('Username').fill('testuser');
    await page.getByRole('button', { name: 'Mock Login' }).click();
  });

  test('should allow reordering exercises in the workout logger', async ({ page }) => {
    // 1. Add two exercises
    await page.getByRole('button', { name: '+ Add Exercise' }).click();
    await page.getByPlaceholder('Search exercise...').fill('Bench Press');
    await page.keyboard.press('Enter');
    
    await page.getByRole('button', { name: '+ Add Exercise' }).click();
    await page.getByPlaceholder('Search exercise...').fill('Squats');
    await page.keyboard.press('Enter');

    // Verify initial order
    const exercises = page.locator('.exercise-row');
    await expect(exercises.first()).toContainText('Bench Press');
    await expect(exercises.nth(1)).toContainText('Squats');

    // 2. Move Squats up
    await page.getByTitle('Move up').last().click();

    // Verify swapped order
    await expect(exercises.first()).toContainText('Squats');
    await expect(exercises.nth(1)).toContainText('Bench Press');

    // 3. Move Bench Press up
    await page.getByTitle('Move up').last().click();
    await expect(exercises.first()).toContainText('Bench Press');
    await expect(exercises.nth(1)).toContainText('Squats');
    
    // 4. Move Bench Press down
    await page.getByTitle('Move down').first().click();
    await expect(exercises.first()).toContainText('Squats');
    await expect(exercises.nth(1)).toContainText('Bench Press');
  });
});
