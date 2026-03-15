# Playwright E2E Testing

description: Playwright E2E standards: role-based locators, auto-waiting, page objects, test isolation, CI integration
tags: testing, playwright, e2e, typescript, javascript, automation, page-objects

Best practices for reliable, maintainable end-to-end tests with Playwright.

## Test Structure

- One test file per feature or user journey
- Group related tests with `test.describe()` blocks
- Use `test.beforeEach()` for common setup
- Aim for 3-5 focused tests per file
- Name tests as user stories: `test('user can log in and see dashboard', ...)`

## Locators — Prefer User-Facing Attributes

Priority order (best to worst):
1. `page.getByRole('button', { name: 'Submit' })` — accessibility role
2. `page.getByLabel('Email address')` — form label
3. `page.getByText('Welcome back')` — visible text
4. `page.getByTestId('submit-btn')` — `data-testid` attribute
5. `page.locator('form > button')` — CSS selector (last resort)

Never use: XPath, positional selectors (`nth-child`), or selectors tied to styling classes.

## Auto-Waiting — No Manual Waits

```typescript
// WRONG — fragile
await page.click('#btn');
await page.waitForTimeout(2000);
await expect(page.locator('.result')).toBeVisible();

// CORRECT — Playwright auto-waits for actionability
await page.getByRole('button', { name: 'Submit' }).click();
await expect(page.getByRole('status')).toHaveText('Saved successfully');
```

- Never use `waitForTimeout()` — it is a test smell
- Use `expect.poll()` only for genuine eventual consistency (e.g., background jobs)

## Test Isolation

- Each test must be independent and deterministic
- Use `test.use({ storageState: 'auth.json' })` for pre-authenticated state
- Reset application state via API or DB before each test — not by navigating through UI
- Use `page.route()` to mock external API calls:
  ```typescript
  await page.route('**/api/users', route =>
    route.fulfill({ json: mockUsers })
  );
  ```

## Page Object Model (POM)

```typescript
// pages/LoginPage.ts
export class LoginPage {
  constructor(private page: Page) {}

  async login(email: string, password: string) {
    await this.page.getByLabel('Email').fill(email);
    await this.page.getByLabel('Password').fill(password);
    await this.page.getByRole('button', { name: 'Log in' }).click();
    await this.page.waitForURL('/dashboard');
  }
}

// tests/auth.spec.ts
test('user can log in', async ({ page }) => {
  const loginPage = new LoginPage(page);
  await loginPage.login('user@example.com', 'password123');
  await expect(page.getByRole('heading')).toHaveText('Dashboard');
});
```

## Assertions

```typescript
// State assertions (auto-retry)
await expect(locator).toBeVisible();
await expect(locator).toHaveText('Expected text');
await expect(locator).toHaveValue('form value');
await expect(page).toHaveURL('/success');
await expect(page).toHaveTitle('My App');

// Negative assertions
await expect(locator).not.toBeVisible();
```

## Configuration

```typescript
// playwright.config.ts
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',
  },
});
```

## CI Integration

```yaml
- name: Install Playwright browsers
  run: npx playwright install --with-deps chromium

- name: Run E2E tests
  run: npx playwright test
  env:
    BASE_URL: http://localhost:3000

- uses: actions/upload-artifact@v4
  if: failure()
  with:
    name: playwright-report
    path: playwright-report/
```
