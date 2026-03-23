import { expect, test } from '@jupyterlab/galata';

test('should register the minio sidebar panel', async ({ page }) => {
  const tab = page.getByRole('tab', { name: 'Minio Browser' });
  await expect(tab).toBeVisible({ timeout: 30000 });
});
