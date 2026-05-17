import { test, expect } from '@playwright/test';

test.describe('set app - error handling', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Login
    await page.getByLabel('Username').fill('testuser');
    await page.getByRole('button', { name: 'Login' }).click();
  });

  test('should show descriptive error when saving a workout fails', async ({ page }) => {
    // Mock the backend API to return a 400 error
    await page.route('**/api/workouts', async route => {
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
    let alertMessage = '';
    page.on('dialog', async dialog => {
      alertMessage = dialog.message();
      await dialog.accept();
    });

    // Save the workout
    await page.getByRole('button', { name: 'Save Workout' }).click();
    
    // Verify the alert message contains the detail and status code
    expect(alertMessage).toContain('Failed to save workout: Invalid workout data (Status: 400)');
  });

  test('should show descriptive error when deleting a workout fails', async ({ page }) => {
    // Mock the backend API to return a list of workouts and then fail on delete
    await page.route('**/api/workouts', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              sk: 'USER#testuser#WORKOUT#2023-01-01T00:00:00Z#mock-id',
              name: 'Delete Me',
              exercises: []
            }
          ])
        });
      } else {
        await route.continue();
      }
    });

    await page.route('**/api/workouts/mock-id*', async route => {
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

    // Handle the confirmation dialog and then the error alert
    let alertMessage = '';
    page.on('dialog', async dialog => {
      if (dialog.type() === 'confirm') {
        await dialog.accept();
      } else {
        alertMessage = dialog.message();
        await dialog.accept();
      }
    });

    // Click delete
    await page.getByTitle('Delete workout').click();
    
    // Verify the alert message contains the detail and status code
    expect(alertMessage).toContain('Failed to delete workout: Permission denied (Status: 403)');
  });
});
