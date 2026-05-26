import { test, expect } from '@playwright/test';

test.describe('Localization', () => {
  test('should display exercise names in Polish in history and routines', async ({ page }) => {
    // 1. Mock exercises with translations
    await page.route('**/exercises', async route => {
      const language = route.request().headers()['accept-language'] || 'en';
      const isPolish = language.startsWith('pl');
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { 
            id: 'Bench_Press', 
            name: 'Bench Press', 
            display_name: isPolish ? 'Wyciskanie leżąc' : 'Bench Press',
            category: 'strength', 
            primaryMuscles: ['chest'],
            translations: { pl: 'Wyciskanie leżąc' }
          }
        ])
      });
    });

    // 2. Mock history (workout)
    await page.route('**/workouts', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            sk: 'WORKOUT#2026-05-26',
            name: 'Morning Workout',
            date: '2026-05-26T10:00:00Z',
            exercises: [
              {
                exercise_id: 'Bench_Press',
                exercise_name: 'Bench Press',
                sets: [{ reps: 10, weight: 60, completed: true }]
              }
            ]
          }
        ])
      });
    });

    // 3. Mock routines
    await page.route('**/routines', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'routine-1',
            name: 'Full Body',
            exercises: [
              {
                exercise_id: 'Bench_Press',
                exercise_name: 'Bench Press',
                sets: [{ reps: 10, weight: 60 }]
              }
            ]
          }
        ])
      });
    });

    // Mock analytics/prs
    await page.route('**/analytics/prs', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            exercise_name: 'Bench Press',
            estimated_1rm: 80,
            max_weight: 60,
            max_volume_set: 600,
            date_achieved: '2026-05-26T10:00:00Z'
          }
        ])
      });
    });

    await page.goto('/');
    // Login
    await page.getByLabel('Username').fill('testuser');
    await page.getByRole('button', { name: 'Mock Login' }).click();

    // Verify English initially
    await page.click('button:has-text("Plan")'); // Navigate to Plan/History view
    await expect(page.locator('.history-item')).toContainText('Bench Press');

    await page.click('button:has-text("Routines")'); // Navigate to Routines view
    await expect(page.locator('.routine-item')).toContainText('Bench Press');

    await page.click('button:has-text("Analytics")'); // Navigate to Analytics view
    await expect(page.locator('.pr-item')).toContainText('Bench Press');

    // 4. Switch to Polish
    await page.click('button:has-text("PL")');

    // 5. Verify Polish translations
    await page.click('button:has-text("Plan")');
    await expect(page.locator('.history-item')).toContainText('Wyciskanie leżąc');

    await page.click('button:has-text("Rutyny")'); // "Routines" becomes "Rutyny"
    await expect(page.locator('.routine-item')).toContainText('Wyciskanie leżąc');

    await page.click('button:has-text("Analityka")'); // "Analytics" becomes "Analityka"
    await expect(page.locator('.pr-item')).toContainText('Wyciskanie leżąc');
  });
});
