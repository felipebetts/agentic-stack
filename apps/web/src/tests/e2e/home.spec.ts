import { expect, test } from '@playwright/test'

test('visitor without a session sees the sign-in form', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByText('Entrar', { exact: true }).first()).toBeVisible()
  await expect(page.getByLabel('Email')).toBeVisible()
  await expect(page.getByLabel('Senha')).toBeVisible()
})
