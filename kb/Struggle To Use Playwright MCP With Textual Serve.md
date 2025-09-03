<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# It's struggling to use Playwright. With Textual Serve, for some reason it's seeing 404s. Meanwhile it's displaying just fine.

Based on the search results and your description of Playwright seeing 404s with Textual Serve while the display works fine, this appears to be a common issue with several potential causes and solutions:

# Textual Serve + Playwright 404 Issues: Diagnosis and Solutions

## The Core Problem

You're experiencing a disconnect between what Playwright detects (404 errors) and what's actually displayed (working correctly). This is a known pattern that occurs with Single Page Applications and WebSocket-based applications like Textual Serve.[^1][^2]

## Why This Happens with Textual Serve

### **Textual Serve Architecture**[^2]

Textual Serve uses a unique architecture:

- Your Textual app runs as a subprocess on the server
- Communication happens via WebSocket protocol
- The browser uses `xterm.js` as a terminal emulator
- ANSI escape sequences are transmitted over WebSocket
- The actual "pages" don't exist as traditional HTTP resources


### **The 404 Pattern**

This creates a scenario where:

1. **Display works fine**: The WebSocket connection delivers content properly
2. **404s occur**: Playwright's HTTP-level checks fail because there are no traditional page resources
3. **Browser doesn't care**: Modern browsers handle WebSocket content regardless of HTTP status

## Solutions and Workarounds

### **1. Configure Playwright to Ignore 404s**

```javascript
// In your Playwright config
await page.route('**/*', (route) => {
  // Let requests through but don't fail on 404s
  route.continue();
});

// Or suppress console errors
page.on('console', (msg) => {
  if (msg.text().includes('404') || msg.text().includes('Not Found')) {
    // Ignore 404 console messages
    return;
  }
  console.log(msg.text());
});
```


### **2. Use WebSocket-Aware Testing**[^3][^4]

Since Textual Serve relies on WebSockets, focus on WebSocket communication rather than HTTP:

```javascript
// Monitor WebSocket connections instead of HTTP
page.on('websocket', (ws) => {
  console.log('WebSocket opened:', ws.url());
  ws.on('framesent', (payload) => console.log('Frame sent:', payload));
  ws.on('framereceived', (payload) => console.log('Frame received:', payload));
});
```


### **3. Wait for WebSocket Connection**[^5]

```javascript
// Wait for WebSocket to establish before testing
await page.waitForFunction(() => {
  return window.WebSocket && 
         Array.from(document.querySelectorAll('*')).some(el => 
           el.textContent && el.textContent.trim().length > 0
         );
}, { timeout: 10000 });
```


### **4. Use Textual-Specific Selectors**

Focus on the terminal content rather than traditional web elements:

```javascript
// Wait for terminal content to load
await page.waitForSelector('.xterm-screen', { timeout: 10000 });

// Wait for specific Textual widget content
await page.waitForFunction(() => {
  const terminal = document.querySelector('.xterm-screen');
  return terminal && terminal.textContent.includes('ExpectedText');
});
```


### **5. Configure Response Handling**[^6]

```javascript
// Handle responses more robustly
page.on('response', (response) => {
  if (response.status() === 404) {
    console.log(`404 on ${response.url()} - this might be expected for Textual Serve`);
    // Don't fail the test
  }
});
```


## Recommended Testing Strategy

### **Focus on Functionality, Not HTTP Status**

```javascript
const { test, expect } = require('@playwright/test');

test('Textual app functionality', async ({ page }) => {
  // Navigate to Textual Serve URL
  await page.goto('http://localhost:8000');
  
  // Wait for WebSocket connection and terminal to load
  await page.waitForSelector('.xterm-screen');
  
  // Wait for app content (adjust selector to your app)
  await page.waitForFunction(() => {
    const screen = document.querySelector('.xterm-screen');
    return screen && screen.textContent.trim().length > 100; // Adjust threshold
  });
  
  // Test interactions through keyboard/mouse events
  await page.keyboard.press('Enter');
  await page.waitForTimeout(100); // Allow for response
  
  // Verify content changes
  const content = await page.textContent('.xterm-screen');
  expect(content).toContain('expected response');
});
```


### **Network Request Filtering**[^7]

```javascript
// Playwright config to handle expected 404s
export default {
  use: {
    // Ignore certain network errors
    ignoreHTTPSErrors: true,
  },
  // Custom handling
  setup: async ({ page }) => {
    page.route('**/static/**', (route) => {
      // Handle static file 404s gracefully
      if (route.request().url().includes('expected-missing-file')) {
        route.fulfill({ status: 200, body: '' });
      } else {
        route.continue();
      }
    });
  }
};
```


## Debugging Approach

1. **Verify WebSocket Connection**: Check if the WebSocket is connecting properly
2. **Monitor Terminal Content**: Focus on `.xterm-screen` content rather than HTTP responses
3. **Use Timing Adjustments**: Add appropriate waits for WebSocket communication
4. **Filter Network Noise**: Ignore expected 404s from static file requests
5. **Test Terminal Behavior**: Simulate keyboard/mouse input and verify terminal responses

The key insight is that Textual Serve's architecture means traditional HTTP-based testing approaches won't work perfectly. The 404s you're seeing are likely expected behavior for this type of WebSocket-based terminal application, and your tests should focus on the actual terminal functionality rather than HTTP status codes.
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^8][^9]</span>

<div style="text-align: center">⁂</div>

[^1]: https://stackoverflow.com/questions/44293044/server-returns-404-for-a-web-page-but-page-is-showing-fine-in-browser-why

[^2]: https://textual.textualize.io/blog/2024/09/08/towards-textual-web-applications/

[^3]: https://www.linkedin.com/pulse/inspect-websockets-playwright-practical-guide-sachith-palihawadana

[^4]: https://playwright.dev/docs/api/class-websocketroute

[^5]: https://testrigor.com/blog/websocketerror-in-playwright/

[^6]: https://www.browserstack.com/guide/playwright-flaky-tests

[^7]: https://playwright.dev/docs/best-practices

[^8]: https://github.com/Textualize/textual-serve/issues

[^9]: https://betterstack.com/community/guides/testing/playwright-best-practices/

[^10]: https://www.reddit.com/r/softwaretesting/comments/1hej5j6/how_do_you_handle_flaky_tests_in_playwright_and/

[^11]: https://www.answeroverflow.com/m/1315318465980010536

[^12]: https://reciteme.com/us/news/best-practices-for-accessibility-testing/

[^13]: https://stackoverflow.com/questions/77074508/playwright-test-not-loading-local-url

[^14]: https://www.programmablebrowser.com/posts/404-checker-playwright/

[^15]: https://www.levelaccess.com/blog/web-accessibility-testing/

[^16]: https://stackoverflow.com/questions/76717436/next-13-app-routing-giving-404-in-playwright-only

[^17]: https://testguild.com/accessibility-testing-tools-automation/

[^18]: https://www.youtube.com/watch?v=6L23XrKaHIw

[^19]: https://it.wisc.edu/learn/make-it-accessible/websites-and-web-applications/testing/

[^20]: https://www.geeksforgeeks.org/blogs/error-404-not-found/

[^21]: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/404

[^22]: https://www.hostinger.com/tutorials/how-to-fix-error-404

[^23]: https://digitaldefynd.com/IQ/testing-api-endpoints/

[^24]: https://owasp.org/www-project-web-security-testing-guide/v41/4-Web_Application_Security_Testing/08-Testing_for_Error_Handling/01-Testing_for_Error_Code

[^25]: https://testsigma.com/blog/test-api-endpoints/

[^26]: https://www.reddit.com/r/learnprogramming/comments/16guorz/new_net_web_app_is_returning_a_404_error_when/

[^27]: https://stackoverflow.com/questions/78588814/playwright-contexts-over-websocket-not-working

