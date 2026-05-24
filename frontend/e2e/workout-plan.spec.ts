import { test, expect } from '@playwright/test';

test.describe('Workout Plan & Progression', () => {
  const today = new Date().toISOString().split('T')[0];

  test.beforeEach(async ({ page }) => {
    // Global mocks to prevent errors
    await page.route('**/exercises', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });
    
    await page.route('**/workouts', async route => {
      if (route.request().method() === 'GET') {
        const history = [{
          sk: `WORKOUT#${today}#uuid-123`,
          name: 'Push Day',
          exercises: []
        }];
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(history) });
      } else {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
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
      day_of_week: 1 // Tuesday (but we just need it to match whatever day next Tuesday is for the plan mock)
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
        date: '2026-05-26', 
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
    await expect(page.locator('h2')).toContainText('Plan');

    // Open scheduling modal
    await page.getByRole('button', { name: 'Schedule Routine' }).click();
    await page.locator('select').first().selectOption({ label: 'Strongman A' });
    await page.getByRole('button', { name: 'Save' }).click();

    // Verify it appears in the list
    await expect(page.locator('.plan-item')).toContainText('Strongman A');
    await expect(page.locator('.plan-item')).toContainText('102.5'); // Verify progressed weight shown in plan
  });

  test('should show historical workouts in calendar view', async ({ page }) => {
    await page.route('**/plan/upcoming', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    });

    // Go to Plan tab
    await page.getByRole('button', { name: 'Plan' }).click();
    
    // Switch to Calendar view
    await page.getByRole('button', { name: 'Calendar' }).click();

    // Verify historical workout appears in calendar
    const dayNumber = new Date().getDate().toString();
    const calendarDay = page.locator('.calendar-day').filter({ has: page.locator('.day-number', { hasText: new RegExp(`^${dayNumber}$`) }) });
    await expect(calendarDay).toContainText('Push Day ✓');
    await expect(calendarDay.locator('.completed')).toBeVisible();
  });
});
