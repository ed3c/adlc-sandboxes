# **現代分散式系統架構下前後端需求拆分、BFF 模式演進與 AI Agent 異步任務調度之深度技術研究報告**

在單頁應用（SPA）與微服務架構普及的背景下，前後端協作的核心範式已從早期的口頭約定演進為以「API 合約（API Contract）」為核心的精密協作體系1。API 合約在工程實踐中扮演著「法律」角色，不僅保障前後端開發團隊得以並行開發，更是釐清責任歸屬、防範分布式數據不一致以及確保系統邊界安全的最高準則2。隨著多端體驗（Multi-device UX）與生成式人工智慧（Generative AI）Agent 的爆發式增長，如何在架構層面科學地拆分系統需求、設計高可靠的通訊協議，並防範高併發交易中的業務邏輯漏洞，成為現代系統架構設計的關鍵課題7。本報告將系統性地探討職責邊界的雙重校驗、需求拆分的實務框架、BFF 模式的演進與安全機制，以及 AI Agent 場景下的長效非同步任務調度技術。

## **職責邊界的灰色地帶：雙重校驗之架構實踐**

在前後端需求拆分中，輸入資料驗證（Data Validation）往往是開發團隊最容易產生糾結與職責模糊的灰色地帶11。正確的架構設計應採取「雙重校驗（Double Validation）」模式，前後端均執行校驗，但兩者的目的、維度與技術實現完全不同11。

### **前端校驗與後端校驗的架構定位**

前端校驗本質上是「體驗驅動」，旨在提升用戶體驗（UX）與交互流暢度12。當用戶輸入不合法的電子郵件格式或強度不足的密碼時，前端應在本地即時觸發視覺提醒，避免無謂的網絡請求往返與使用者等待12。前端校驗屬於防禦性交互，本質上是「貼心」的設計4。  
後端校驗則是「安全驅動」，旨在維護系統的安全邊界（Security Boundary）與數據一致性4。在零信任（Zero Trust）網絡架構下，系統絕不能信任來自前端的任何輸入4。惡意攻擊者可輕易繞過前端用戶界面，利用 Postman、cURL 或腳本直接向後端 API 發送惡意構造的數據4。例如，惡意將商品數量修改為負數（如 ![][image1] 件）或將結帳金額修改為 ![][image2] 元4。後端必須執行絕對嚴格的防禦性校驗，此為不可妥協的「必須」要求4。

### **Monorepo 與共享 Schema 解決方案**

傳統開發中，前後端各自編寫驗證規則會導致「校驗邏輯漂移（Validation Drift）」14。一旦業務規則變更，開發團隊必須同步修改兩套代碼，極易產生疏漏14。當前業界的主流解決方案是在單一代碼倉庫（Monorepo，如 Turborepo 或 pnpm Workspaces）中建立一個共享合約套件14。  
利用 TypeScript 優先的宣告式 Schema 庫（例如 Zod、TypeBox 或 Yup），開發團隊可將資料合約、靜態型別與運行時驗證邏輯封裝在單一源頭12。

TypeScript  
// packages/contracts/src/auth.ts  
import { z } from 'zod';

export const UserLoginSchema \= z.object({  
  email: z.string().email({ message: "無效的電子郵件格式" }),  
  password: z.string().min(8, { message: "密碼長度不足 8 位" })  
});

export type UserLoginInput \= z.infer\<typeof UserLoginSchema\>;

在 Fastify 或 NestJS 等後端伺服器中，該 Schema 可直接作為運行時路由攔截的校驗規則14，而在 React/Next.js 前端中，該 Schema 則可直接無縫集成至表單校驗庫（如 React Hook Form）中14。這使兩端共享完全一致的業務語義，變更規則時僅需更新共享 Schema12。  
在持續集成（CI）管線中，開發團隊應結合 **Schemathesis** 或 **Pact** 等工具進行自動化合約測試，驗證後端實現是否與 OpenAPI 規範完全契合，防止任何未說明的 API 變更引發系統性崩潰15。

| 比較維度 | 前端校驗 (Frontend Validation) | 後端校驗 (Backend Validation) |
| :---- | :---- | :---- |
| **核心目的** | 提升用戶體驗（UX），降低交互延遲12 | 保護系統安全（Security），保障數據庫完整性4 |
| **信賴層級** | 零信賴（客戶端環境易受操縱與偽造）4 | 絕對信任源（系統運行的最後防線）4 |
| **典型攻擊面** | 無法抵禦直接的 API 級別繞過攻擊4 | 攔截並阻斷一切繞過 UI 的 cURL、Postman 及腳本注入4 |
| **驗證邏輯範疇** | 基礎格式、必填項、即時密碼強度、前端關聯欄位12 | 商務規則、權限、防重入、數據庫事務約束與狀態完整性4 |
| **常用技術組件** | Zod, Formik, React Hook Form12 | Zod, Express/Fastify Validator, Spring @Validated5 |

## **關注點分離：需求拆分框架與四步驟實務模型**

前後端拆分的本質是關注點分離（Separation of Concerns），旨在將外觀展現與核心業務運算完全解耦，使系統具備優異的擴展性與可維護性4。

### **前後端職責劃分原則**

前端主要負責「怎麼呈現」與「用戶互動」26。其職責包括 UI/UX 佈局與視覺動畫、客戶端狀態管理（如緩存與前端 Context）、基礎表單校驗，以及基於防重複點擊的優化機制（如 Debounce 與 Throttle）26。  
後端則負責「業務邏輯」、「數據安全」與「持久化」4。其職責包括核心商務演算法、身分識別與權限校驗（Authentication/Authorization）、資料庫事務（Transaction）處理、第三方服務整合（如金流、物流對接）以及重度效能計算4。

### **電商優惠券折抵需求拆分之四步驟模型**

為了具體展示需求拆分框架的實作，本報告以電商系統中的典型 User Story 進行分析：「用戶在電商網站點擊『領取優惠券』並在結帳時自動折抵。」26

                             \[ API Contract \]  
                     (RESTful JSON / GraphQL Schema)  
                                    |  
\[ Frontend (UI/UX) \] \<=============++=============\> \[ Backend (Business & DB) \]  
  \- 按鈕防重擊 (Throttle)                             \- 資格與限額校驗 (Check)  
  \- 打包購物車與券代碼                                \- 分散式扣減庫存 (Deduct)  
  \- 渲染折抵成功/失敗 UI                              \- 金額計算與事務寫入 (Order)

#### **步驟一：分析 User Story**

本故事包含兩個高風險的操作：高頻率的領券動作（面臨秒殺級瞬時流量）以及結帳時的金額計算與狀態變更（面臨資安與強一致性要求）26。

#### **步驟二：定義前端職責**

前端需設計優惠券領取按鈕，並實施 Throttle 限制以防範用戶重複點擊26。結帳時，前端負責打包當前購物車中的商品列表、數量及所選的優惠券代碼，調用結帳 API26。收到後端回傳的最終訂單計算結果或錯誤狀態後，前端異步渲染出對應的成功支付界面或錯誤警告提示，避免本地計算金額直接影響核心結帳結果26。

#### **步驟三：定義後端職責**

後端接收到請求後，首先調用身分與權限模組驗證用戶權限，隨後進入促銷與優待券引擎，核對該用戶是否符合該優惠券的領取與使用資格25。在資料庫事務內，執行原子化的優惠券庫存扣減，防止超賣（Overselling）9。後端會根據資料庫記錄的商品原價重新計算扣減後的最終金額，並安全地寫入訂單與支付紀錄9。

#### **步驟四：制定 API 合約**

在動工開發前，前後端技術專家共同制定 API 傳輸合約，定義好 Request/Response 的 JSON 結構26。合約確立後，前後端即可使用 **Mock Service Worker (MSW)** 或 **Prism** 獨立開展工作3。

JSON  
// POST /api/v1/checkout/apply-coupon  
// Request Payload  
{  
  "cart\_id": "cart\_88721",  
  "coupon\_code": "DISCOUNT100",  
  "idempotency\_key": "idemp\_uuid\_772199"  
}

// Response Payload (200 OK)  
{  
  "order\_id": "ord\_99012",  
  "original\_amount": 1200,  
  "discount\_amount": 100,  
  "final\_amount": 1100,  
  "status": "PENDING\_PAYMENT"  
}

### **高併發交易的併發漏洞（Race Conditions）防禦**

在電商與高頻交易場景中，並發請求極易引發時間差漏洞（Time-of-Check to Time-of-Use, TOCTOU），攻擊者常利用並發請求實現「優惠券重複兌換（Coupon Abuse）」或「雙重提現（Double Spending）」9。若後端代碼採取傳統的先查詢、後寫入（Check-then-Act）設計，多個並發事務可能會讀取到同一個「未使用」的狀態快照，並同時通過資格檢查，進而導致嚴重的資產損失25。  
為杜絕此漏洞，後端系統必須在持久層引入強併發控制手段25：

1. **原子更新與條件約束（Atomic Updates）**：利用資料庫原生鎖機制，執行 Check-and-Update 的單一 SQL 語句，並驗證受影響行數25：  
   SQL  
   UPDATE coupons SET is\_used \= 1, used\_at \= NOW()   
   WHERE code \= :code AND is\_used \= 0;

2. **悲觀鎖（Pessimistic Locking）**：在高爭搶的庫存扣減或餘額操作中，使用 SELECT ... FOR UPDATE 強制對相關行加鎖，使並發事務串行化執行25。  
3. **分散式鎖（Distributed Locking）**：在涉及多個獨立微服務協調的架構下，利用 Redis 的 SETNX 原語（或 Redlock 演算法）對特定用戶的身分或優惠券代碼加鎖，確保同一秒內只有一個請求能進入業務核心25。

## **多端時代的演進：BFF (Backend for Frontend) 模式的架構設計**

隨著客戶端的多端化發展（Web 官網、iOS App、Android App、智慧穿戴等），傳統的前後端分離模式面臨著嚴重的架構瓶頸7。

### **BFF 模式的誕生背景**

多端設備的螢幕物理尺寸、交互方式與網路帶寬環境存在巨大差異7。例如，手機移動端螢幕較小，為減少網路往返（RTT）與節省帶寬，需要精簡、高密度的數據 Payload7；而網頁端螢幕寬廣，需要調用多個微服務獲取極為豐富的關聯資訊進行大版面渲染7。  
若強行讓所有客戶端調用同套通用後端 API，前端將面臨嚴重的過度獲取（Overfetching，下載不必要數據）或獲取不足（Underfetching，調用 3、4 個不同的 API 才能拼湊出一個畫面）的問題，導致移動端因多次建立 HTTP 連接而載入遲緩7。為了克服這一痛點，Backend for Frontend（BFF）架構模式應運而生7。

                     \[ Client / SPA Tier \]  
      Web App (Large Screen)       Mobile App (Small Screen)  
              |                               |  
        \[ Web BFF \]                     \[ Mobile BFF \]  
        (Node.js/Go)                    (Node.js/Go)  
         /    |    \\                     /    |    \\  
        /     |     \\                   /     |     \\  
\[ Product \] \[ Cart \] \[ Promo \]   \[ Product \] \[ Cart \] \[ Promo \]  
                     \[ Core Microservices Tier \]

7

### **BFF 的職責與設計原則**

BFF 是一個專門為「特定前端體驗」量身打造的微型後端服務層（通常採用異步 I/O 能力強勁的 Node.js 或 Go 撰寫）7：

* **職責拆分與角色定位**：  
  * **客戶端**：不再直接對接複雜的核心微服務，僅向專屬的 BFF 服務發起請求並負責最終 UI 渲染7。  
  * **BFF 層**：負責為對應前端進行「數據聚合（Data Aggregation）」、格式裁剪與裁剪轉換7。BFF 將多個微服務的響應拼裝成最適合該客戶端尺寸與布局的單一 JSON Payload7。BFF 應保持無狀態（Stateless），嚴禁掛載數據庫或保留業務狀態34。  
  * **核心後端**：保持純粹與穩定，專注於通用業務邏輯、演算法、事務處理與數據持久化7。  
* **關鍵架構原則**：BFF 的設計應遵循「一端一 BFF（One BFF Per Client Type）」原則8。若將 Web、Mobile 等多個性質迥異的客戶端強行綁定在同一個 BFF 上，該 BFF 將迅速退化為一個新的通用單體網關，破壞團隊獨立演進的核心優勢8。同時，**BFF 的所有權應屬於前端開發團隊**，確保 API 合約能緊跟 UI 交互的疊代節奏快速變更，無需與後端底層團隊反覆溝通協調8。

### **BFF 與 API 網關（API Gateway）的權責分野**

在實際部署中，BFF 與 API 網關通常是協同工作、互不取代的。API 網關屬於橫向、服務導向（Service-Centric）的網路基礎設施；而 BFF 則是縱向、體驗導向（Client-Centric）的應用層組件8。

| 特徵維度 | API 網關 (API Gateway) | BFF 服務層 (Backend for Frontend) |
| :---- | :---- | :---- |
| **設計核心** | 服務導向（Service-Centric）38 | 客戶端/體驗導向（Client-Centric）38 |
| **維護團隊** | 平台基礎設施/運維團隊（Platform/Infra Team）8 | 前端/產品交付團隊（Frontend Product Team）8 |
| **典型技術** | Kong, AWS API Gateway, Nginx, APISIX8 | Node.js, Go, GraphQL (Apollo Server)7 |
| **橫向切面職責** | SSL 終端、全域負載均衡、DDoS 防護、流量路由37 | 屏幕 Payload 適配、微服務異步扇出（Fan-out）、協議轉換37 |
| **安全控制** | 全域 rate-limiting、API 密鑰校驗37 | 用戶 Session 管理、OAuth 2.0 安全 Session 轉換7 |

### **基於 BFF 的 OAuth 2.0 安全防護實踐**

隨著 Web 應用的複雜度增加，防範跨站腳本攻擊（XSS）以保護敏感的身分標記（Access/Refresh Tokens）已成為架構設計的重中之重45。在 SPA 中直接儲存 Token 會使其暴露在被惡意腳本直接讀取的巨大風險之下45。因此，安全界大力推行基於 BFF 的 Token 安全儲存架構45。  
在此架構下，BFF 扮演「機密客戶端（Confidential Client）」的角色45：

1. **授權與協商**：BFF 與身份授權伺服器（IDP）對接，安全地儲存 Client Secret，並負責完整的 OAuth 2.0 Authorization Code Flow 與 PKCE 校驗45。  
2. **安全存儲**：一旦完成認證，IDP 發放的 Access Token 與 Refresh Token 將被保存在後端的加密 Session Store（如 Redis）或直接進行加密打包45。  
3. **無 Token 傳輸**：BFF 對前端瀏覽器僅發放一個代表會話的 Session Cookie45。該 Cookie 必須嚴格配置以下防禦屬性以確保極致安全47：  
   * HttpOnly：禁止 JavaScript 讀取，規避 XSS 竊取45。  
   * Secure：強制僅在安全加密信道（HTTPS）下傳送47。  
   * SameSite=Strict 或 Lax：防止跨站請求偽造（CSRF）47。  
   * \_\_Host- 前綴命名：防範子網域毒化與跨子域 Cookie 覆蓋47。  
4. **代理與轉發**：當 SPA 調用受保護的 API 時，請求發送至 BFF。BFF 解析 Session Cookie 後，從安全的後端緩存中調出對應的 Access Token，將其寫入 HTTP 的 Authorization: Bearer 頭中，隨後轉發給下游核心微服務46。

## **AI Agent 場景下的長效非同步任務：前端焦慮緩解與後端高能調度**

在 Agentic AI 工作流中，AI Agent 的執行流程通常需要經過「鏈式思考（Chain of Thought, CoT）」、動態調用多個外部網絡爬蟲、執行代碼沙箱，甚至調用多個子代理進行協作10。此時，單個請求的執行時長可輕易突破數十秒甚至數分鐘52。

### **前後端協作機制：體驗優化與背景調度**

面對這種類型的「長效型非同步任務」，傳統的同步 HTTP 請求/響應（Request-Response）模式會因為網絡連線長時間掛起而極易超時，且會迅速耗盡伺服器端的線程池資源53。因此，架構師必須設計一套精準的異步解耦調度方案53：

* **前端（解決用戶等待焦慮）**：前端的核心職責在於，將後端 Agent 複雜、黑盒的思考鏈，轉化為流暢、可預期的「進度視覺化」10。透過實時的動態看板、思考步驟狀態標記（例如「正在查詢數據源...」、「正在分析 Q4 財報...」、「正在生成摘要...」），讓用戶對系統的當前運作狀態有清晰的掌控，從而緩解漫長等待帶來的負面焦慮感10。  
* **後端（背景高能調度與系統保護傘）**：後端則要像一個穩重的調度員，將耗時的 LLM 推理、文件生成等任務，安頓在背景的異步線程或分散式 Worker 隊列（如 Celery、Arq 或 Temporal）中執行53。後端 API 接收到用戶的 Agent 執行指令後，應立即生成任務唯一的 Task\_ID 並寫入隊列，然後迅速向前端響應 HTTP 202 Accepted53。背景 Worker 獨立異步運行，並通過進度緩存與事件分發機制與前端通信53。後端必須扮演好 Agent 與底層資料庫之間的「保護傘」，防止大量失控的 Agent 並發查詢直接將底層數據庫衝垮4。

### **長效任務通訊機制技術評估：Polling vs. SSE vs. WebSockets**

針對此長效非同步任務的即時進度同步，系統架構團隊需要在 **短輪詢（Polling）**、**伺服器發送事件（SSE）** 與 **WebSockets** 之間做出嚴格的架構取捨54。

#### **1\. 短輪詢（Short Polling）**

* **機制**：客戶端利用 setInterval，每隔一定時間（例如 5 秒）主動向後端 API 發送 HTTP GET 請求，查詢任務狀態與進度55。  
* **優勢**：極易實現，對既有網絡架構與負載均衡器無任何特殊要求，具備完全的無狀態特徵，易於水平擴展55。  
* **劣勢**：造成帶寬浪費，產生海量無效的 HTTP 請求頭交互55。在併發量高達十萬級的環境下，後端伺服器將被大量的輪詢請求「擊穿」，且狀態更新的即時性受限於間隔時間，用戶體驗存在顯著的頓挫感55。

#### **2\. 伺服器發送事件（SSE, Server-Sent Events）**

* **機制**：基於標準 HTTP 協議（Content-Type 為 text/event-stream），客戶端一次發起，伺服器保持單向長連接，以 UTF-8 文本流形式持續推送數據55。  
* **現代技術加持：HTTP/3 與 QUIC 協議下的 SSE**： 在 HTTP/1.1 時代，瀏覽器有單一域名最多 6 個 TCP 連接限制，且面臨嚴重的 TCP 隊頭阻塞（Head-of-Line Blocking）54。但在 **HTTP/3 (QUIC)** 協議下，這一切限制已被徹底打破54：  
  * **徹底解決隊頭阻塞**：QUIC 基於 UDP，其在傳輸層實現了真正獨立的多路復用流，一個 SSE 流的網絡丟包絕不會阻塞其他分析流或通知流的傳輸54。  
  * **零握手延遲（0-RTT）**：連線建立速度顯著優於傳統協議54。  
  * **原生自動重連**：SSE 協議內置自動重連與 Last-Event-ID 機制，客戶端一旦異常斷線，瀏覽器會自動攜帶歷史事件 ID 發起重連，後端能無縫補發重連期間斷失的 Token 流，無需手動編寫重試緩衝邏輯55。  
  * **無狀態水平擴展**：由於是單向 HTTP 連接，服務端維持的狀態極輕，清理無效連接極其迅速（生成器結束拋出 GeneratorExit 即刻回收資源）54，這使 SSE 能完美適配 Serveless Edge Computing（如 Cloudflare Workers Vercel Edge）進行無感知的彈性伸縮54。

#### **3\. 雙向 WebSockets**

* **機制**：客戶端與伺服器通過 HTTP 手動 Upgrade 為基於 TCP 的全雙工、對等通訊協議51。  
* **隱藏的「架構稅（Infrastructure Tax）」**： 雖然 WebSockets 能提供極低延遲的雙向實時交互，但對長效 AI 任務而言，它會帶來巨大的運作複雜度與基礎設施開銷54：  
  * **橫向擴展與廣播困境**：WebSockets 屬於強狀態（Stateful）物理長連接54。若將系統水平擴展至數百個 K8s Pod，當背景 Worker A 完成了用戶 X 的任務，由於用戶 X 的 WebSocket 連接維持在 Pod B 上，Pod A 無法直接推送消息給用戶。系統必須強制引入 Redis Pub/Sub、NATS 或 Kafka 作為跨節點廣播的中介，這使得網絡拓撲與代碼維護成本直線上升54。  
  * **Session Affinity（會話親和性）問題**：AI Agent 與工具調用通常需要維護上下文親和性（Session Affinity），一旦網絡切換（如移動端用戶在地鐵中斷開重連），WebSocket 難以維護原連接狀態，需要配合 Cookie 或自定義 MCP 頭實現複雜的 L7 智能調度路由52。  
  * **高昂的狀態維護代價**：伺服器必須維持每一個 Socket 的內存上下文，且極易遭受殭屍連線（Zombie Sockets）的內存蠶食54。

| 技術評估維度 | 短輪詢 (Short Polling) | 伺服器發送事件 (SSE) | 雙向 WebSockets |
| :---- | :---- | :---- | :---- |
| **通訊流向** | 客戶端單向高頻請求55 | 伺服器單向長效推送流55 | 客戶端與伺服器雙向全雙工51 |
| **底層傳輸協議** | 標準 HTTP (REST)55 | 標準 HTTP（完美發揮 HTTP/3 優勢）54 | 自定義 WS 協議 (HTTP Upgrade 轉換)51 |
| **帶寬與連接開銷** | 極高，充滿空數據包與重複 Headers55 | 極低，維持單一連接，僅在有數據時傳輸54 | 極低（建立連線後無 HTTP 冗餘）54 |
| **中斷與故障恢復** | 需要前端代碼自行編寫重試輪詢 | **是**（瀏覽器原生自動重連並保證事件 ID 連續性）55 | 否（需手動編寫 Heartbeat、Ping-Pong 與重連緩衝）55 |
| **水平擴展能力** | 極易（天然無狀態）55 | **易**（配合 HTTP/3 的輕量無狀態擴展，極佳）54 | 困難（必須配套架設 Redis Pub/Sub 消息中介）54 |
| **AI Agent 最佳契合點** | 慢速、非時間敏感的背景工作報告查詢53 | **最優解**（流式 Token 生成、CoT 進度實時動態推送）10 | 語音/視頻流同步交互、多人在線實時白板、高頻協同51 |

### **AI Agent 異步任務調度之數學模型**

在設計背景 Worker 調度時，我們可以通过數學模型來評估並行調度與序列調度對系統吞吐量及平均響應時間（Latency）的影響。  
設一個 AI Agent 任務需要調用 ![][image3] 個相互獨立的子工具或大模型推理，每個子任務的執行時長為 ![][image4] (![][image5])，BFF 對這些子服務的網絡調用建立時間為 ![][image6]。  
若採用傳統的**序列調度模式（Sequential Execution）**，任務必須逐個阻塞執行，總延遲為44：  
![][image7]  
若在 BFF 層中實施**並行非同步調度（Parallel Fan-out Execution）**（例如在 Node.js 中使用 Promise.all），則總執行延遲完全由執行最慢的子任務決定，並行化後的總延遲優化為44：  
![][image8]  
在實際部署中，對於一個包含 4 個子 Agent 鏈式運算的請求，並行非同步調度能為系統節省 ![][image9] 的整體響應時間44，大幅釋放伺服器線程，從而極大地改善了高併發場景下 AI 應用的服務可用性與前端用戶的流暢體驗感。

## **結論**

在前後端協作體系向深水區演進的過程中，系統架構的可靠性與擴展性取決於職責邊界的清晰界定。

1. **API 合約是並行疊代的法律標準**1。通過在 Monorepo 中利用 Zod 等工具共享 Schema，團隊能夠將運行時的數據安全防線與編譯期的靜態型別約束緊密鎖定，徹底杜絕前後端邏輯不一致與 Schema 漂移14。  
2. **BFF 是多端時代解決多樣化體驗的最佳架構模式，更是網頁安全的首選防護牆**7。通過將 BFF 作為 OAuth 2.0 的機密客戶端，將敏感的 Token 管理與 Session Cookie 機制完全留在安全網域內，系統能夠在不變更核心微服務的前提下，為前端構築最堅固的安全防線45。  
3. **對於複雜的 AI Agent 場景，長效非同步任務是維持系統穩定的唯一途徑**53。前端應致力於流暢的進度視覺化以緩解等待焦慮10，而後端則應通過背景異步隊列進行保護性調度53。在通訊協議的選擇上，基於 HTTP/3 且內置自動重連機制的 SSE，在擴展性、維護難度與整體架構開銷上，均顯著優於強狀態的 WebSockets 協議，是現代 AI 系統工程實踐中的最優解54。

#### **引用的著作**

1. Design-Driven APIs \- wal.sh, [https://wal.sh/research/design-driven-apis?w=1](https://wal.sh/research/design-driven-apis?w=1)  
2. Stop Building APIs Without a Contract — How Contract-First, [https://designgurus.substack.com/p/openapi-protobuf-and-graphql-how](https://designgurus.substack.com/p/openapi-protobuf-and-graphql-how)  
3. An introduction to spec-driven API development \- Apideck, [https://www.apideck.com/blog/spec-driven-development-part-1](https://www.apideck.com/blog/spec-driven-development-part-1)  
4. Vertical Slicing & Clean Architecture: A Practical Guide for Elysia Developers · GitHub, [https://gist.github.com/RezaOwliaei/477ed74fc77aa5df2a854789538dd79d](https://gist.github.com/RezaOwliaei/477ed74fc77aa5df2a854789538dd79d)  
5. Contract-First with Spring Boot: A Modern Approach to API Development \- Medium, [https://medium.com/@rodrigoventuri123/contract-first-with-spring-boot-a-modern-approach-to-api-development-f1a1635cf95b](https://medium.com/@rodrigoventuri123/contract-first-with-spring-boot-a-modern-approach-to-api-development-f1a1635cf95b)  
6. Using Swagger to Mock APIs for Faster Development \- Reintech, [https://reintech.io/blog/using-swagger-to-mock-apis-for-faster-development](https://reintech.io/blog/using-swagger-to-mock-apis-for-faster-development)  
7. Backend for Frontend (BFF) Pattern: Microservices for UX | Teleport, [https://goteleport.com/learn/backend-for-frontend-bff-pattern/](https://goteleport.com/learn/backend-for-frontend-bff-pattern/)  
8. Backend for Frontend (BFF) Pattern \- gist/GitHub, [https://gist.github.com/carefree-ladka/2e2a4bfab5c16a7a8f2cb094ccc8d442](https://gist.github.com/carefree-ladka/2e2a4bfab5c16a7a8f2cb094ccc8d442)  
9. Race Conditions | Security Categories \- Sourcery, [https://www.sourcery.ai/security/categories/race\_conditions](https://www.sourcery.ai/security/categories/race_conditions)  
10. Make 'em visible\! See what is happening inside your agentic workflow \- DEV Community, [https://dev.to/aws-builders/make-em-visible-see-what-is-happening-inside-your-agentic-workflow-27la](https://dev.to/aws-builders/make-em-visible-see-what-is-happening-inside-your-agentic-workflow-27la)  
11. SRA/.gemini/skills/zod/SKILL.md at main · Aniket-a14/SRA · GitHub, [https://github.com/Aniket-a14/SRA/blob/main/.gemini/skills/zod/SKILL.md](https://github.com/Aniket-a14/SRA/blob/main/.gemini/skills/zod/SKILL.md)  
12. Yup Validation Explained: Schemas, TypeScript, Best Practices, and Real-World Use Cases, [https://uptimerobot.com/knowledge-hub/devops/yup-validation-explained/](https://uptimerobot.com/knowledge-hub/devops/yup-validation-explained/)  
13. API schema validation: contract testing for REST and GraphQL | Bug0, [https://bug0.com/knowledge-base/api-schema-validation](https://bug0.com/knowledge-base/api-schema-validation)  
14. Sharing Types and Validations with Zod Across a Monorepo | Leapcell, [https://leapcell.io/blog/sharing-types-and-validations-with-zod-across-a-monorepo](https://leapcell.io/blog/sharing-types-and-validations-with-zod-across-a-monorepo)  
15. Contract Testing vs. Schema Validation: Know the Difference | Nordic APIs |, [https://nordicapis.com/contract-testing-vs-schema-validation-know-the-difference/](https://nordicapis.com/contract-testing-vs-schema-validation-know-the-difference/)  
16. Cursor rules in multi-project workspaces \- Bug Reports, [https://forum.cursor.com/t/cursor-rules-in-multi-project-workspaces/129557](https://forum.cursor.com/t/cursor-rules-in-multi-project-workspaces/129557)  
17. FlashLearn \- Teron Bullock, [https://teronbullock.com/project/flashcard-study-app/](https://teronbullock.com/project/flashcard-study-app/)  
18. One Type System to Rule Them All. How to wire NestJS \+ Next.js so your… | by Praxen | Medium, [https://medium.com/@Praxen/one-type-system-to-rule-them-all-f902bb33e2ca](https://medium.com/@Praxen/one-type-system-to-rule-them-all-f902bb33e2ca)  
19. Types in Typescript should make your life easier | Casual Programming, [https://casual-programming.com/20251217\_types\_in\_typescript\_should\_make\_your\_life\_easier/](https://casual-programming.com/20251217_types_in_typescript_should_make_your_life_easier/)  
20. Life's too short to hand-write API types: OpenAPI-driven React \- Evil Martians, [https://evilmartians.com/chronicles/lifes-too-short-to-hand-write-api-types-openapi-driven-react](https://evilmartians.com/chronicles/lifes-too-short-to-hand-write-api-types-openapi-driven-react)  
21. API Mocking Tools for Developers Compared | DevToolReviews, [https://www.devtoolreviews.com/reviews/api-mocking-tools-for-developers](https://www.devtoolreviews.com/reviews/api-mocking-tools-for-developers)  
22. Schemathesis, [https://schemathesis.readthedocs.io/](https://schemathesis.readthedocs.io/)  
23. Automated API Testing with Schemathesis: Let Your OpenAPI Spec Do the Work, [https://www.davidmello.com/software-testing/test-automation/automated-api-testing-with-schemathesis](https://www.davidmello.com/software-testing/test-automation/automated-api-testing-with-schemathesis)  
24. 7 OpenAPI/JSON-Schema Moves for Python Contract Testing | by Modexa \- Medium, [https://medium.com/@Modexa/7-openapi-json-schema-moves-for-python-contract-testing-1fdd1f7e201f](https://medium.com/@Modexa/7-openapi-json-schema-moves-for-python-contract-testing-1fdd1f7e201f)  
25. Race Condition / TOCTOU \- Offensive360, [https://offensive360.com/knowledge-base/race-condition/](https://offensive360.com/knowledge-base/race-condition/)  
26. E-commerce Architecture and System Design for E-commerce Websites \- GeeksforGeeks, [https://www.geeksforgeeks.org/system-design/e-commerce-architecture-system-design-for-e-commerce-website/](https://www.geeksforgeeks.org/system-design/e-commerce-architecture-system-design-for-e-commerce-website/)  
27. YS CART WordPress E-commerce Built for the Taiwan Market \- YANGSHEEP CLOUD, [https://yangsheep.com.tw/en/ys-cart/](https://yangsheep.com.tw/en/ys-cart/)  
28. Microservices Architecture Best Practices | PDF | Databases \- Scribd, [https://www.scribd.com/document/713143885/Design-Microservices-v2](https://www.scribd.com/document/713143885/Design-Microservices-v2)  
29. Ecommerce Architecture: The Ultimate Guide for 2026 (Frameworks, Costs & Checklists), [https://rbmsoft.com/blogs/ecommerce-architecture/](https://rbmsoft.com/blogs/ecommerce-architecture/)  
30. Business Logic Security \- OWASP Cheat Sheet Series, [https://cheatsheetseries.owasp.org/cheatsheets/Business\_Logic\_Security\_Cheat\_Sheet.html](https://cheatsheetseries.owasp.org/cheatsheets/Business_Logic_Security_Cheat_Sheet.html)  
31. Mocking APIs for Testing: Accelerating Development and Improving Quality \- API7.ai, [https://api7.ai/learning-center/api-101/mocking-apis-for-testing-purposes](https://api7.ai/learning-center/api-101/mocking-apis-for-testing-purposes)  
32. 12 Questions and Answers About Race Condition \- Security Scientist, [https://www.securityscientist.net/blog/12-questions-and-answers-about-race-condition/](https://www.securityscientist.net/blog/12-questions-and-answers-about-race-condition/)  
33. Business Logic Vulnerability Testing \- Application Security Authority, [https://applicationsecurityauthority.com/business-logic-vulnerability-testing/](https://applicationsecurityauthority.com/business-logic-vulnerability-testing/)  
34. Backend for Frontend (BFF): The Complete Engineering Guide | by Kaizen Chandra, [https://medium.com/@code.chandrashekhar/backend-for-frontend-bff-the-complete-engineering-guide-f9d924984559](https://medium.com/@code.chandrashekhar/backend-for-frontend-bff-the-complete-engineering-guide-f9d924984559)  
35. NetSuite Headless Commerce: Guide to Sub-Second API Speed \- Houseblend.io, [https://www.houseblend.io/articles/netsuite-headless-commerce-api-guide](https://www.houseblend.io/articles/netsuite-headless-commerce-api-guide)  
36. Do you need a Backend For Frontend? \- Marmelab, [https://marmelab.com/blog/2025/10/01/do-you-need-a-backend-for-frontend.html](https://marmelab.com/blog/2025/10/01/do-you-need-a-backend-for-frontend.html)  
37. API Gateway vs Backend For Frontend (BFF) \- GeeksforGeeks, [https://www.geeksforgeeks.org/system-design/api-gateway-vs-backend-for-frontend-bff/](https://www.geeksforgeeks.org/system-design/api-gateway-vs-backend-for-frontend-bff/)  
38. Understanding the Core Differences Between API Gateways and BFFs | Leapcell, [https://leapcell.io/blog/understanding-the-core-differences-between-api-gateways-and-bffs](https://leapcell.io/blog/understanding-the-core-differences-between-api-gateways-and-bffs)  
39. Backend for Frontend Pattern in Elevating Microservices in Enterprise Architecture, [https://www.architectureandgovernance.com/elevating-ea/backend-for-frontend-pattern-in-elevating-microservices-in-enterprise-architecture/](https://www.architectureandgovernance.com/elevating-ea/backend-for-frontend-pattern-in-elevating-microservices-in-enterprise-architecture/)  
40. Backends for Frontends | arc42 Quality Model, [https://quality.arc42.org/approaches/backends-for-frontends](https://quality.arc42.org/approaches/backends-for-frontends)  
41. The BFF Pattern: Friendship Goals for Frontend and Backend | Architect View Master, [https://www.architectviewmaster.com/blog/bff-pattern-friendship-goals-frontend-backend/](https://www.architectviewmaster.com/blog/bff-pattern-friendship-goals-frontend-backend/)  
42. Architecture Essentials — API Gateway Vs BFF Pattern | by Sandeep Sharma | Medium, [https://medium.com/@sandeepsharmaster/architecture-essentials-api-gateway-vs-bff-pattern-ee6b8f0d7318](https://medium.com/@sandeepsharmaster/architecture-essentials-api-gateway-vs-bff-pattern-ee6b8f0d7318)  
43. A Pragmatic Journey from Monolith to Microservices | by Mehmet Ozkaya | Medium, [https://mehmetozkaya.medium.com/a-pragmatic-journey-from-monolith-to-microservices-309271d8e54d](https://mehmetozkaya.medium.com/a-pragmatic-journey-from-monolith-to-microservices-309271d8e54d)  
44. Microservices Patterns : Backend for Frontend (BFF) | by Abhinav Thakur | Medium, [https://medium.com/@abhi.strike/microservices-patterns-backend-for-frontend-bff-fca5dc2b5bbd](https://medium.com/@abhi.strike/microservices-patterns-backend-for-frontend-bff-fca5dc2b5bbd)  
45. OAuth 2.0 for Browser-Based Apps: BFF vs. TMB \- Orchitech, [https://orchi.tech/en/blog/2026/03/30/oauth-2-0-for-browser-based-applications-bff-tmb/](https://orchi.tech/en/blog/2026/03/30/oauth-2-0-for-browser-based-applications-bff-tmb/)  
46. Securing your web apps: Spring security OAuth 2.0 \+ BFF pattern \- ProductDock, [https://productdock.com/securing-your-web-apps-spring-security-oauth-2-0-bff-pattern/](https://productdock.com/securing-your-web-apps-spring-security-oauth-2-0-bff-pattern/)  
47. Every Frontend Needs Its Backend: OAuth2 Token Security in Single-Page Applications, [https://www.devoteam.com/be/expert-view/every-frontend-needs-its-backend/](https://www.devoteam.com/be/expert-view/every-frontend-needs-its-backend/)  
48. The Backend for Frontend Pattern (BFF) | Auth0, [https://auth0.com/blog/the-backend-for-frontend-pattern-bff/](https://auth0.com/blog/the-backend-for-frontend-pattern-bff/)  
49. Things Developers Get Wrong About the Backend for Frontend Pattern \- Auth0, [https://auth0.com/blog/things-developers-get-wrong-about-the-backend-for-frontend-pattern/](https://auth0.com/blog/things-developers-get-wrong-about-the-backend-for-frontend-pattern/)  
50. Why MQTT Is the Missing Infrastructure Layer for Agentic AI | EMQ \- EMQX, [https://www.emqx.com/en/blog/why-mqtt-is-the-missing-infrastructure-layer-for-agentic-ai](https://www.emqx.com/en/blog/why-mqtt-is-the-missing-infrastructure-layer-for-agentic-ai)  
51. Way Back Home \- Building an ADK Bi-Directional Streaming Agent \- Google Codelabs, [https://codelabs.developers.google.com/way-back-home-level-3/instructions](https://codelabs.developers.google.com/way-back-home-level-3/instructions)  
52. Production-Ready MCP \#2: Gateway Architecture & Federated Registries \- TM Dev Lab, [https://www.tmdevlab.com/mcp-gateway-architecture-enterprise.html](https://www.tmdevlab.com/mcp-gateway-architecture-enterprise.html)  
53. Background Task Queue in an AI Application \- Gist, [https://gist.github.com/mkbctrl/6b32dbb6eca34edc32d23a5b865304ed](https://gist.github.com/mkbctrl/6b32dbb6eca34edc32d23a5b865304ed)  
54. Streaming Architecture in 2026: Beyond WebSockets \- Jet BI, [https://jetbi.com/blog/streaming-architecture-2026-beyond-websockets](https://jetbi.com/blog/streaming-architecture-2026-beyond-websockets)  
55. Frontend System Design: Communication Protocols & Real-Time Data \- DEV Community, [https://dev.to/zeeshanali0704/frontend-system-design-communication-protocols-real-time-data-h7h](https://dev.to/zeeshanali0704/frontend-system-design-communication-protocols-real-time-data-h7h)  
56. HTTP and Server-Sent Events · Cloudflare Agents docs, [https://developers.cloudflare.com/agents/runtime/communication/http-sse/](https://developers.cloudflare.com/agents/runtime/communication/http-sse/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAZCAYAAAAv3j5gAAAA3UlEQVR4AeyUMQrCQBBFVcROrbSwsbK0tbWy8wJ2XsAbCGIreACvINrZCt7AAwiKV7C28C0ki8HsZCNDirDhPyYws/N3pthapaAvGP29aO3VjbmJgZCUhtGEljt4wAVG8CMNoxZdz7AEpzSMjnTfwx2c0jByNv9OlNeozpg9T7rUSaqmJePVDUluPdlQZy5GSJVodOXIzJM5dW/IpXiiXIcyisWJMs56pRtRVTOKiaAx0ZqONzjACxbwhBNYaRit6DaADrTBPEl94hSsNIxsM+knGEnbEXNhdeJ6pOQHAAD//xGC3kIAAAAGSURBVAMAiNMaMx695R4AAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAaCAYAAACO5M0mAAABL0lEQVR4AdSSP0tCURjGL0UUtUQUfYBoaIjmICqIpragtfoE7Q2NNQStQWNDUB+gpTUaWhoaqi38h4qgIqgIiv6el/teDoLiqPL+zvs89zzXc3xxKhrxMyZBXWOfK1/AKaxAUtqUmWG5gTP4h1V4gk2w8uAR7hju4R1eIAPXMA2RB88xBfiCKqThDQ5gAyy4gNiDHHTAK4WYhx2w4BJiEeoQViM26+o6elkC2hCWe/v1Cs6Gu4HuxloTsaP9CL0U71lzb1eSKfFYb8/Rw3Jf1EMFywjNzO+KtXL/LadgC/EKa6Bx0Ky2WPPwAXZH9UeWGpyABqzZbaMfIAtJ8BNzB9rcpR/CH9yClY42wfIMl/AD0lf0JliFQT2osOhP8Uv3gSOj5Ggzw5b+bxyYnYRgDwAA//9Hl2bvAAAABklEQVQDAGVvMDVw5BKSAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAaCAYAAABVX2cEAAABaUlEQVR4AeyTPS8FQRSGL1H4aJRqhJDohRDEH9CKRk3lN6g1CgkKEoVWL74SGolKEBKRiBARUYmGeJ7r7tqdHQXR3XvzPntm5sx9Z/bsTH3pH39VajZGCa/hHh5gA0IdM3ADV+DcBWJZYc12GG2HfWiESeiArPrprIELDhHnoKzQrDzIoxfmoQ5mIKt3Oi60SLyDVDGzbrIXsAqvMA3NkNUgHXdP+FbMbIT0HryANWslTkGiJhot8Ag5/WS2W5nlq9ic9VFhgHgEBcXMeph1DuqUh7vsIw6DcufJYvZTQjPrdZlmvxrh7jQr1Mupodkog+6EkGqL1i1MQBdYsydiQTGzcFWPwhL/bIB1OISosmaeKWtzFpm5wtgbeGCj9SJXypr5+d2Fpuay+FqbDHzAAUSl2TgZ7+EysROewTtKyMkP4b00n0skHc226bSBhRUPqXeUoZxO6PmahLg0i2f+MFoz+33RqqRmnwAAAP//eoNNJgAAAAZJREFUAwBi3Do10MSC6AAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAbCAYAAACnZAX6AAABTElEQVR4AeSSzSpGURSGT0QxwowyIQMppBj4S8nfxJUguQO34A5kJiOlSDGQGJsQioEQI0pkIM+zs0+f850OGalP77PWXmvtt33s/VUlf/irBNMA97IMhcpexCK7R6BQpaY6dk7CBRRKUz07mmEQmuAMrKvJudI0xmQOluADusC6gZwrTVdMDqAVXG+Qrd/IudJ0ymQPGuEItr94IUd1svCTSUmiyUUHoQU8gVSmaTplpiGa6tCQwzm9BwiKJ41S3cElqBmCsxqy73ZNvoEgBy56CSfwDt7eOFn1EbygeXKqaLqnUwvDMAW74PW3k2+hH1JF0wodh57iZ+xQq2PCLGxBqmjapOODrpLXIeqRxQQ4byMHRZPFMyH7oD6Dv0n/127mQaWm0MiEJ+p96IH4yenj0suVF7TAZA1eIeink9yUbraQ35jc941/bvoEAAD//4HTwLIAAAAGSURBVAMAR4Q0N1UK7k4AAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,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>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAaCAYAAABRqrc5AAABcUlEQVR4AeySO0sDQRSFF1EQFBvBVvBViIWF2tgIClaCaKuWFmJnJdoICiIKFirYWAj+AXvxARYi2AhpUwUCIZBAihRJyHc2mc3sJpAdSJEi4Xz37p3MnNy9mT6vA5+eSfMQozNZY8szOClqcsbpaXCSbTLMySX4BCfJZIQTU7AJ/ZAEdTNAjiWZ7LDzHq6gBFtwB2MQSzJ5YOc6qINfsp5FiudYkok2DhEWwXkenPGMyTKFZvBBdpYxWeGk5vFNdpZt8sfpAkhPBP1Tk+QbmIUNuIADCMmYTLD6D9I+IQHqbJf8A3rNPPkcjkFXglSTMbml3IZHGIdrkF4Jc/ACX1AB3SvTMaUXDPaSagaO4ASM9Iqa13t9YZWsLtPkQKYTLWQIoV+gHoQFUBckT3NRd3sUo+DLNvEXImGeWhcwR5ayBA1ZF1HPlI3X8YsWQQa6vearUx4O4Q0CteukzM4i2NK/ZNfBYEOLrkW7TmL5dY9JFQAA//84JhzYAAAABklEQVQDAB5INjWngsLsAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,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>

[image9]: <data:image/png;base64,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>