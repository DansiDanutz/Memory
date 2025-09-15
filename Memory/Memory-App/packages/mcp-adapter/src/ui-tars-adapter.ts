// UI-TARS Adapter - Browser automation and UI interaction via MCP
import puppeteer, { Browser, Page } from 'puppeteer';
import { UITarsAction, UITarsResult } from './types';
import { MCPClient } from './mcp-client';

export class UITarsAdapter {
  private mcpClient: MCPClient;
  private browser: Browser | null = null;
  private activePage: Page | null = null;

  constructor(mcpClient: MCPClient) {
    this.mcpClient = mcpClient;
  }

  async initialize(): Promise<void> {
    try {
      // Initialize headless browser for UI automation
      this.browser = await puppeteer.launch({
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--disable-gpu'
        ]
      });

      this.activePage = await this.browser.newPage();
      
      // Set viewport for consistent screenshots
      await this.activePage.setViewport({
        width: 1280,
        height: 720
      });

      console.log('✅ UI-TARS browser initialized');
    } catch (error) {
      console.error('❌ Failed to initialize UI-TARS browser:', error);
      throw error;
    }
  }

  async cleanup(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
      this.browser = null;
      this.activePage = null;
      console.log('🧹 UI-TARS browser cleaned up');
    }
  }

  async executeAction(action: UITarsAction): Promise<UITarsResult> {
    if (!this.activePage) {
      return {
        success: false,
        error: 'Browser not initialized',
        timestamp: Date.now()
      };
    }

    try {
      const result: UITarsResult = {
        success: true,
        timestamp: Date.now()
      };

      switch (action.type) {
        case 'navigate':
          if (!action.value) {
            throw new Error('Navigate action requires a URL value');
          }
          await this.activePage.goto(action.value, { 
            waitUntil: 'networkidle2',
            timeout: 30000
          });
          result.screenshot = await this.takeScreenshot();
          break;

        case 'click':
          if (action.selector) {
            await this.activePage.click(action.selector);
          } else if (action.coordinates) {
            await this.activePage.mouse.click(action.coordinates.x, action.coordinates.y);
          } else {
            throw new Error('Click action requires either selector or coordinates');
          }
          await new Promise(resolve => setTimeout(resolve, 1000)); // Wait for UI updates
          result.screenshot = await this.takeScreenshot();
          break;

        case 'type':
          if (!action.selector || !action.value) {
            throw new Error('Type action requires selector and value');
          }
          await this.activePage.type(action.selector, action.value);
          result.screenshot = await this.takeScreenshot();
          break;

        case 'scroll':
          if (action.coordinates) {
            await this.activePage.mouse.wheel({ deltaY: action.coordinates.y });
          } else {
            await this.activePage.evaluate(() => {
              (globalThis as any).window.scrollBy(0, 300);
            });
          }
          result.screenshot = await this.takeScreenshot();
          break;

        case 'screenshot':
          result.screenshot = await this.takeScreenshot();
          break;

        case 'extract':
          if (!action.selector) {
            throw new Error('Extract action requires a selector');
          }
          const elements = await this.activePage.$$(action.selector);
          const extractedData = await Promise.all(
            elements.map(async (element) => {
              const text = await element.evaluate(el => el.textContent);
              const attributes = await element.evaluate(el => {
                const attrs: Record<string, string> = {};
                for (const attr of el.attributes) {
                  attrs[attr.name] = attr.value;
                }
                return attrs;
              });
              return { text: text?.trim(), attributes };
            })
          );
          
          result.extractedData = extractedData;
          result.screenshot = await this.takeScreenshot();
          break;

        default:
          throw new Error(`Unsupported action type: ${action.type}`);
      }

      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown UI action error',
        timestamp: Date.now()
      };
    }
  }

  private async takeScreenshot(): Promise<string> {
    if (!this.activePage) {
      throw new Error('No active page for screenshot');
    }
    
    const screenshot = await this.activePage.screenshot({
      encoding: 'base64',
      fullPage: false
    });
    
    return screenshot as string;
  }

  async getCurrentUrl(): Promise<string> {
    if (!this.activePage) {
      throw new Error('No active page');
    }
    
    return this.activePage.url();
  }

  async getPageTitle(): Promise<string> {
    if (!this.activePage) {
      throw new Error('No active page');
    }
    
    return this.activePage.title();
  }

  async evaluateJavaScript(script: string): Promise<any> {
    if (!this.activePage) {
      throw new Error('No active page');
    }
    
    return this.activePage.evaluate(script);
  }

  // Helper method for multi-step automation workflows
  async executeWorkflow(actions: UITarsAction[]): Promise<UITarsResult[]> {
    const results: UITarsResult[] = [];
    
    for (const action of actions) {
      const result = await this.executeAction(action);
      results.push(result);
      
      // Stop on first failure
      if (!result.success) {
        break;
      }
      
      // Add small delay between actions
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    return results;
  }

  // Advanced extraction using accessibility data
  async extractAccessibleData(selector?: string): Promise<any> {
    if (!this.activePage) {
      throw new Error('No active page');
    }

    return this.activePage.evaluate((sel: string | undefined) => {
      const doc = (globalThis as any).document;
      const elements = sel ? doc.querySelectorAll(sel) : [doc.body];
      const accessibleData: any[] = [];
      
      elements.forEach((element: any) => {
        if (element && element.tagName) {
          accessibleData.push({
            tag: element.tagName.toLowerCase(),
            text: element.textContent?.trim(),
            ariaLabel: element.getAttribute('aria-label'),
            role: element.getAttribute('role'),
            id: element.id,
            className: element.className,
            href: element.tagName.toLowerCase() === 'a' ? element.href : null,
            src: element.tagName.toLowerCase() === 'img' ? element.src : null
          });
        }
      });
      
      return accessibleData;
    }, selector);
  }

  // Integration with MCP for advanced UI operations
  async getMCPUICapabilities(): Promise<any> {
    if (this.mcpClient.isConnected('ui-tars')) {
      try {
        const tools = await this.mcpClient.listTools('ui-tars');
        return {
          connected: true,
          tools: tools.map(tool => tool.name),
          capabilities: tools
        };
      } catch (error) {
        return {
          connected: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
    
    return {
      connected: false,
      localCapabilities: ['navigate', 'click', 'type', 'scroll', 'screenshot', 'extract'],
      note: 'Using local Puppeteer implementation'
    };
  }

  isInitialized(): boolean {
    return this.browser !== null && this.activePage !== null;
  }
}