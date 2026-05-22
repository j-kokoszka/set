import { test, expect } from '@playwright/test';

test.describe('set app - error handling', () => {
  test.beforeEach(async ({ page }) => {
<<<<<<< HEAD
    // Mock the backend exercises endpoint
=======
    // Mock exercises
>>>>>>> origin/main
    await page.route('**/exercises', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
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

    await page.goto('/');
    // Login
    await page.getByLabel('Username').fill('testuser');
    await page.getByRole('button', { name: 'Mock Login' }).click();
  });

  test('should show descriptive error when saving a workout fails', async ({ page }) => {
    // Mock the backend API to return a 400 error
    await page.route('**/workouts', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid workout data' })
        });
      } else {
        await route.continue();
      }
    });

    // Set workout name
    await page.getByPlaceholder('Workout Name').fill('Error Test Workout');

    // Click add exercise
    await page.getByRole('button', { name: '+ Add Exercise' }).click();
    await page.getByPlaceholder('Search exercise...').fill('Squats');
    await page.keyboard.press('Enter');
    
    // Add a set
    await page.getByRole('button', { name: '+ Set' }).click();

    // Handle the browser alert
    const alertPromise = page.waitForEvent('dialog');

    // Save the workout
    await page.getByRole('button', { name: 'Save Workout' }).click();
    
    const alert = await alertPromise;
    // Verify the alert message contains the detail and status code
    expect(alert.message()).toContain('Failed to save workout: Invalid workout data (Status: 400)');
    await alert.accept();
  });

  test('should show descriptive error when deleting a workout fails', async ({ page }) => {
    // Mock the backend API to return a list of workouts and then fail on delete
    await page.route('**/workouts', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              sk: 'WORKOUT#2023-01-01T00:00:00Z#mock-id',
              name: 'Delete Me',
              exercises: []
            }
          ])
        });
      } else {
        await route.continue();
      }
    });

    await page.route('**/workouts/mock-id*', async route => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Permission denied' })
        });
      } else {
        await route.continue();
      }
    });

    // Go to history
    await page.getByRole('button', { name: 'History' }).click();
    await expect(page.locator('.card', { hasText: 'Delete Me' })).toBeVisible();

    // Handle the confirmation dialog automatically
    page.once('dialog', dialog => {
      void dialog.accept();
    });

    // Wait for the subsequent error alert
    const alertPromise = page.waitForEvent('dialog', dialog => dialog.type() === 'alert');

    // Click delete
    await page.getByTitle('Delete workout').click();
    
    const alert = await alertPromise;
    // Verify the alert message contains the detail and status code
    expect(alert.message()).toContain('Failed to delete workout: Permission denied (Status: 403)');
    await alert.accept();
  });
});
