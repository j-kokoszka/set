import { test, expect } from '@playwright/test';

test.describe('Workout Plan & Progression', () => {
  test.beforeEach(async ({ page }) => {
    // Global mocks to prevent errors
    await page.route('**/exercises', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/workouts', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    await page.route('**/routines', async route => {
      const routines = [{
        id: 'routine-1',
        name: 'Strongman A',
        exercises: [{
          exercise_name: 'Squat',
          sets: [{ reps: 5, weight: 100, unit: 'kg' }],
          progression: { enabled: true, increment_weight: 2.5, condition: 'all_completed' }
        }]
      }];
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(routines) });
    });
    
    // Login
    await page.goto('/');
    await page.getByPlaceholder('Username').fill('testuser');
    await page.getByRole('button', { name: 'Mock Login' }).click();
  });

  test('should be able to schedule a routine and view it in the plan', async ({ page }) => {
    // Mock the schedules and plan endpoints
    const mockSchedule = {
      id: 'sched-1',
      routine_id: 'routine-1',
      routine_name: 'Strongman A',
      schedule_type: 'recurring',
      day_of_week: 1 // Tuesday
    };
    
    await page.route('**/schedules', async route => {
      if (route.request().method() === 'POST') {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockSchedule) });
      } else {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([mockSchedule]) });
      }
    });

    await page.route('**/plan/upcoming', async route => {
      const plan = [{
        date: '2026-05-26', // A Tuesday
        routine: {
          id: 'routine-1',
          name: 'Strongman A',
          exercises: [{
            exercise_name: 'Squat',
            sets: [{ reps: 5, weight: 102.5, unit: 'kg' }] // Progressed
          }]
        },
        is_recurring: true
      }];
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(plan) });
    });

    // Go to Plan tab
    await page.getByRole('button', { name: 'Plan' }).click();
    await expect(page.locator('h2')).toContainText('Workout Plan');

    // Open scheduling modal
    await page.getByRole('button', { name: 'Schedule Routine' }).click();
    await page.locator('select').first().selectOption({ label: 'Strongman A' });
    await page.getByRole('button', { name: 'Save' }).click();

    // Verify it appears in the list
    await expect(page.locator('.plan-item')).toContainText('Strongman A');
    await expect(page.locator('.plan-item')).toContainText('102.5'); // Verify progressed weight shown in plan
  });
});
