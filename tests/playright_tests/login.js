test('test', async ({ page }) => {
  await page.goto('http://localhost:8003/accounts/login/?next=/');
  await page.getByRole('textbox', { name: 'Username' }).click();
  await page.getByRole('textbox', { name: 'Username' }).fill('admin');
  await page.getByRole('textbox', { name: 'Username' }).press('Tab');
  await page.getByRole('textbox', { name: 'Password' }).fill('password');
  await page.getByRole('textbox', { name: 'Password' }).press('Tab');
  await page.getByRole('button', { name: 'Login' }).press('Tab');
  await page.getByRole('link', { name: 'Github (opens in new tab)' }).press('Shift+Tab');
  await page.getByRole('button', { name: 'Login' }).press('Enter');
  await page.getByRole('button', { name: 'Login' }).click();
});