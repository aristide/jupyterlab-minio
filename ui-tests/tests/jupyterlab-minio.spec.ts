import { test, expect } from '@playwright/test';

test('should register the minio sidebar panel', async ({ page }) => {
  await page.goto('http://localhost:8888/lab');
  const tab = page.getByRole('tab', { name: 'Minio Browser' });
  await expect(tab).toBeVisible({ timeout: 60000 });
});
