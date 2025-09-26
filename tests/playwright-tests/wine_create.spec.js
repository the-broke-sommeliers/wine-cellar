import { test, expect } from '@playwright/test';

test.describe('Wine creation flow', () => {
  test.beforeEach(async ({ page }) => {
    // Log in first
    await page.goto('http://localhost:8003/accounts/login/?next=/');
    await page.getByRole('textbox', { name: 'Username' }).fill('admin');
    await page.getByRole('textbox', { name: 'Password' }).fill('password');
    await page.getByRole('button', { name: 'Login' }).click();

    // Go to "Add Wine"
    await page.getByRole('link', { name: 'Add Wine' }).click();
  });

  test('can create a new wine with required fields', async ({ page }) => {
    await page.getByRole('textbox', { name: 'Name' }).fill('Vino Del Blanco');
    await page.getByLabel('Wine type').selectOption('DE');
    await page.getByLabel('Country').selectOption('ES');
    await page.getByLabel('Size').selectOption({ index: 4 }); // pick a size via dropdown

    await page.getByRole('button', { name: 'Continue' }).click();

    // ✅ Assert that we’re on the next step
    await expect(page.getByText('Grapes (Optional)')).toBeVisible();
  });

  test('can add optional details (grapes, vintage, abv, sweetness)', async ({ page }) => {
    await page.getByRole('textbox', { name: 'Name' }).fill('Reserva Especial');
    await page.getByLabel('Wine type').selectOption('DE');
    await page.getByLabel('Country').selectOption('ES');
    await page.getByLabel('Size').selectOption({ index: 4 });

    await page.getByRole('button', { name: 'Continue' }).click();

    // Fill optional details
    await page.getByLabel('Grapes (Optional)').selectOption('2');
    await page.getByRole('spinbutton', { name: 'Vintage (Optional)' }).fill('1999');
    await page.getByRole('spinbutton', { name: 'Abv (Optional)' }).fill('12.5');
    await page.getByLabel('Sweetness (Optional)').selectOption('SD');

    await page.getByRole('button', { name: 'Continue' }).click();

    // click through remaining steps
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByRole('button', { name: 'Continue' }).click();

    // ✅ Final assertion – confirm wine was created
    await expect(page.getByText('Wine successfully added')).toBeVisible();
  });
});
