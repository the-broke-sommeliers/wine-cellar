import { test, expect } from '@playwright/test';

test.describe('Wine filters', () => {
  test.beforeEach(async ({ page }) => {
    // Log in first
    await page.goto('http://localhost:8003/accounts/login/?next=/');
    await page.getByRole('textbox', { name: 'Username' }).fill('admin');
    await page.getByRole('textbox', { name: 'Password' }).fill('password');
    await page.getByRole('button', { name: 'Login' }).click();

    // Go to "Add Wine"
    await page.getByRole('link', { name: 'Wines' }).click();
  });

  test('can filter by wine type', async ({ page }) => {
    await page.getByRole('combobox', { name: 'Wine type' }).click();
    await page.locator('#id_wine_type-opt-2').click();
    await page.locator('#id_wine_type-opt-2').selectOption('RE');
    await page.getByRole('button', { name: 'Filter', exact: true }).click();

    // ✅ Add an assertion – example: results should update
    await expect(page.getByText('Results')).toBeVisible();

    // reset
    await page.getByRole('button', { name: 'Clear all filters and reset' }).click();
  });

  test('can filter by country', async ({ page }) => {
    await page.getByRole('combobox', { name: 'Country' }).click();
    await page.locator('#id_country-opt-5').click();
    await page.locator('#id_country-opt-5').selectOption('AX');
    await page.getByRole('button', { name: 'Filter', exact: true }).click();

    await expect(page.getByText('Results')).toBeVisible();

    await page.getByRole('button', { name: 'Clear all filters and reset' }).click();
  });

  test('can filter by grapes', async ({ page }) => {
    await page.getByRole('combobox', { name: 'Grapes' }).click();
    await page.locator('#id_grapes-opt-2').click();
    await page.locator('#id_grapes-opt-2').selectOption('2');
    await page.getByRole('button', { name: 'Filter', exact: true }).click();

    await expect(page.getByText('Results')).toBeVisible();

    await page.getByRole('button', { name: 'Clear all filters and reset' }).click();
  });

  test('can filter by source', async ({ page }) => {
    await page.getByRole('combobox', { name: 'Source' }).click();
    await page.locator('#id_source-opt-1').click();
    await page.locator('#id_source-opt-1').selectOption('1');
    await page.getByRole('button', { name: 'Filter', exact: true }).click();

    await expect(page.getByText('Results')).toBeVisible();

    await page.getByRole('button', { name: 'Clear all filters and reset' }).click();
  });
});