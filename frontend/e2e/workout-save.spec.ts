import { test, expect } from '@playwright/test';

test.describe('set app - workout saving', () => {
  test.beforeEach(async ({ page }) => {
    // Mock the backend API responses
    await page.route('**/api/workouts', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Workout saved!' })
        });
      } else if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              sk: `WORKOUT#${new Date().toISOString()}#mock-id`,
              name: 'Leg Day E2E',
              exercises: [{ exercise_name: 'Squats', sets: [1] }]
            }
          ])
        });
      } else {
        await route.continue();
      }
    });

    await page.goto('/');
    // Login
    await page.getByLabel('Username').fill('testuser');
    await page.getByRole('button', { name: 'Mock Login' }).click();
  });

  test('should allow creating and saving a workout', async ({ page }) => {
    // Set workout name
    await page.getByPlaceholder('Workout Name').fill('Leg Day E2E');

    // Click add exercise
    await page.getByRole('button', { name: '+ Add Exercise' }).click();
    
    // Fill exercise name and add
    await page.getByPlaceholder('Search exercise...').fill('Squats');
    await page.keyboard.press('Enter');
    
    // Add a set
    await page.getByRole('button', { name: '+ Set' }).click();
    
    // Fill weight and reps
    const weightInput = page.getByPlaceholder('0').first();
    await weightInput.fill('100');
    
    const repsInput = page.getByPlaceholder('0').nth(1);
    await repsInput.fill('10');

    // Handle the browser alert that appears on save
    page.on('dialog', dialog => dialog.accept());

    // Save the workout
    await page.getByRole('button', { name: 'Save Workout' }).click();
    
    // After saving, the view should switch to history and show the workout
    await expect(page.locator('.history-list')).toBeVisible();
    await expect(page.locator('.card', { hasText: 'Leg Day E2E' })).toBeVisible();
    await expect(page.locator('.card', { hasText: 'Squats' })).toBeVisible();
  });
});
