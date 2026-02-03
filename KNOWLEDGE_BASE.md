# 🧠 CORE KNOWLEDGE BASE - Modern Development Resources

**Updated**: February 2, 2026  
**Total Resources**: 120+  
**Categories**: Frontend, Backend, Database, Testing, DevOps, Build Tools, Linting, Email, APIs, Learning

---

## 🎯 PRIORITIZED STACK (Top 10%)

**Default Modern Stack for New Projects:**
- Next.js 15+ App Router (https://nextjs.org/docs)
- tRPC (https://tRPC.io/docs)
- Prisma/Drizzle ORM (https://www.prisma.io/docs)
- Zod Validation (https://zod.dev/)
- Tailwind CSS (https://tailwindcss.com/docs)
- Shadcn UI (https://ui.shadcn.com/docs)
- Vitest (https://vitest.dev/guide)
- Playwright (https://playwright.dev/docs/intro)
- Docker (https://docs.docker.com/get-started)
- GitHub Actions (https://docs.github.com/en/actions)

---

## 🎨 FRONTEND RESOURCES (30)

### Frameworks & Meta-frameworks
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://react.dev/learn | Core | HIGH | Official React 18+ docs with hooks & concurrent features |
| https://beta.reactjs.org/reference/react | Reference | HIGH | React API reference with latest patterns |
| https://nextjs.org/docs | Framework | CRITICAL | Next.js 15+ App Router, Server Components, Edge Runtime |
| https://remix.run/docs | Framework | HIGH | Remix run on edge, nested routing, forms |
| https://nuxt.com/docs | Framework | MEDIUM | Vue 3 meta-framework, auto-imports, server-first |
| https://astro.build/docs | Framework | MEDIUM | Zero-JS by default, island architecture |
| https://qwik.dev/docs | Framework | LOW | Resumable, no hydration, micro-frontends |

### State Management
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://tanstack.com/query/latest/docs/framework/react/overview | Data Fetching | HIGH | React Query for server state, caching, optimistic updates |
| https://tanstack.com/router/latest/docs/framework/react/overview | Routing | HIGH | Type-safe client routing with data loading |
| https://tanstack.com/table/latest/docs/guide/introduction | Table | MEDIUM | Headless table with sorting, filtering, virtualization |
| https://redux.js.org/ | State | MEDIUM | Redux Toolkit, RTK Query, DevTools |
| https://recoiljs.org/docs/introduction/installation | State | LOW | Atomic state, derived state, snapshots |
| https://mobx.js.org/README.html | State | LOW | Reactive, observable state management |
| https://zustand-demo.pmnd.rs/ | State | HIGH | Simple, lightweight, no context needed |

### UI Component Libraries
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://ui.shadcn.com/docs | Components | CRITICAL | Radix UI primitives, fully customizable, copy-paste |
| https://mui.com/material-ui/getting-started/overview | Components | MEDIUM | Material Design 3, comprehensive component set |
| https://chakra-ui.com/docs/getting-started | Components | MEDIUM | Accessible, themeable, composable |
| https://ant.design/docs/react/introduce | Components | MEDIUM | Enterprise-focused, comprehensive |
| https://mantine.dev/pages/getting-started | Components | LOW | 70+ components, theming system |
| https://headlessui.com/ | Primitives | HIGH | Unstyled, accessible, fully customizable |
| https://radix-ui.com/docs/primitives/overview/introduction | Primitives | HIGH | Unstyled, accessible, headless UI |

### Styling & Animation
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://tailwindcss.com/docs | CSS | CRITICAL | Utility-first, responsive, dark mode support |
| https://www.framer.com/motion/ | Animation | HIGH | Production-ready motion, layout, drag, gestures |
| https://greensock.com/docs/ | Animation | MEDIUM | GSAP, ScrollTrigger, high-performance |
| https://floating-ui.com/docs/installation | Positioning | HIGH | Tooltip, popover, dropdown positioning |
| https://motionbgs.com | Backgrounds | LOW | Animated gradients & backgrounds |
| https://anime.js | Animation | LOW | Lightweight animation library |
| https://cssgridgenerator.io | Generator | LOW | CSS Grid layout generator |

### Forms & Validation
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://react-hook-form.com/get-started | Forms | CRITICAL | Performant, flexible, type-safe forms |
| https://formik.org/docs/overview | Forms | MEDIUM | Schema-based form builder |
| https://zod.dev/ | Validation | CRITICAL | TypeScript-first, composable schemas |
| https://yup.dev/ | Validation | MEDIUM | Schema validation, TypeScript types |
| https://github.com/colinhacks/zod | Validation | HIGH | Zod alternatives & patterns |

### Testing
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://storybook.js.org/docs | UI Testing | MEDIUM | Component development, visual testing, docs |
| https://vitest.dev/guide | Testing | CRITICAL | Vite-native, fast, TypeScript first |
| https://jestjs.io/docs/getting-started | Testing | HIGH | Jest ecosystem, mocking, coverage |
| https://playwright.dev/docs/intro | E2E | CRITICAL | Cross-browser, headless, auto-waiting |
| https://www.cypress.io/how-it-works | E2E | HIGH | Time-travel debugging, real browser |
| https://testing-library.com/docs/react-testing-library/intro | Unit | CRITICAL | User-centric testing, accessibility first |
| https://mswjs.io/docs | Mocking | HIGH | API mocking, network interception |

### Meta-Resources
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://github.com/sindresorhus/awesome | Lists | HIGH | Curated list of awesome libraries |
| https://github.com/enaqx/awesome-react | Lists | HIGH | React-specific awesome list |

---

## 🔧 BACKEND RESOURCES (25)

### Node.js Runtimes
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://nodejs.org/en/docs | Runtime | HIGH | Node.js docs, ES modules, stability |
| https://bun.sh | Runtime | HIGH | All-in-one toolkit, native TypeScript |

### API Frameworks
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://expressjs.com/en/starter/installing.html | Framework | MEDIUM | Minimal, unopinionated, mature ecosystem |
| https://fastify.dev/docs/latest/Guides/Getting-Started/ | Framework | HIGH | Fast, schema-based, TypeScript first |
| https://nestjs.com/ | Framework | HIGH | Opinionated, modular, decorators |
| https://hono.dev/getting-started/nodejs | Framework | HIGH | Lightweight, Edge runtime, type-safe |
| https://elysiajs.com/ | Framework | MEDIUM | Fast, cookie support, middleware |

### APIs & GraphQL
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://tRPC.io/docs | API | CRITICAL | End-to-end type safety, no codegen |
| https://www.apollographql.com/docs/apollo-server | GraphQL | HIGH | Federation, subscriptions, cache |
| https://the-guild.dev/graphql/yoga-server/docs | GraphQL | HIGH | Spec compliant, GraphQL over HTTP |
| https://graphql.org/learn | Learning | HIGH | GraphQL concepts, best practices |

### Realtime & HTTP
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://socket.io/docs/v4/index.html | WebSockets | HIGH | Realtime, fallbacks, rooms, auth |
| https://github.com/typicode/json-server | Mock API | LOW | JSON placeholder, full REST, filtering |
| https://github.com/http-party/node-http-proxy | Proxy | LOW | HTTP proxy, websockets, HTTPS |

### Documentation & APIs
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://github.com/Redocly/redoc | Docs | MEDIUM | OpenAPI docs, three-panel layout |
| https://swagger.io/tools/open-source/ | Docs | HIGH | Swagger UI, OpenAPI spec |
| https://editor.swagger.io/ | Editor | MEDIUM | API spec editor |
| https://www.postman.com/api-platform/api-client/ | Tool | HIGH | API client, testing, mocking |

### Utilities & Middleware
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://github.com/remix-run/serve | Static | LOW | Static file serving |
| https://github.com/expressjs/morgan | Logging | LOW | HTTP request logger |
| https://github.com/fastify/fast-json-stringify | JSON | LOW | Fast JSON stringify |
| https://github.com/fastify/fastify-swagger | Docs | LOW | Swagger for Fastify |

---

## 🗄️ DATABASE RESOURCES (20)

### Node.js ORMs
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://www.prisma.io/docs | ORM | CRITICAL | TypeScript-first, schema migration, studio |
| https://typeorm.io/ | ORM | HIGH | Active Record pattern, decorators |
| https://sequelize.org/master/ | ORM | MEDIUM | Promise-based, migrations |
| https://www.drizzle.team/docs/overview | ORM | HIGH | SQL-like, TypeScript, migrations |
| https://mongoosejs.com/docs/ | ODM | MEDIUM | MongoDB, schema validation |
| https://knexjs.org/guide/ | Query Builder | MEDIUM | SQL query builder, migrations |
| https://kysely.dev/docs/ | Query Builder | MEDIUM | Type-safe SQL, migrations |

### Python ORMs
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://www.sqlalchemy.org/library.html | ORM | HIGH | Python SQL toolkit, ORM |
| https://www.django-rest-framework.org/ | Framework | HIGH | Django REST, authentication, permissions |

### NoSQL & Search
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://www.doctrine-project.org/projects/doctrine-orm/en/3.6/reference/query-builder.html | ORM | LOW | PHP ORM, DQL |
| https://www.mongodb.com/docs/drivers/node/current/ | Driver | MEDIUM | MongoDB Node.js driver |

### Cache & Search
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://redis.io/docs/latest/develop/ | Cache | HIGH | In-memory data store, pub/sub |
| https://www.elastic.co/guide/index.html | Search | HIGH | Elasticsearch, Kibana, Logstash |

### SQL Databases
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://www.postgresql.org/docs | SQL | HIGH | Advanced RDBMS, JSON, extensions |
| https://dev.mysql.com/doc | SQL | HIGH | Popular RDBMS, replication |
| https://www.sqlite.org/docs.html | SQL | HIGH | Embedded, zero-config |
| https://clickhouse.com/docs | SQL | MEDIUM | OLAP, column-oriented |
| https://www.influxdata.com/blog/influxdb-v3-docs | TSDB | LOW | Time-series database |

### BaaS & Services
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://supabase.com/docs | BaaS | HIGH | PostgreSQL, Auth, Storage, Edge Functions |

### Meta-Resources
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://www.prisma.io/dataguide/database-tools/top-nodejs-orms-query-builders-and-database-libraries | List | HIGH | Top Node.js ORMs list |

---

## 🧪 TESTING RESOURCES (15)

### JavaScript Testing
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://vitest.dev/guide | Framework | CRITICAL | Vite-native, fast, TypeScript |
| https://jestjs.io/docs/getting-started | Framework | HIGH | Jest ecosystem, snapshots, mocks |
| https://playwright.dev/docs/intro | E2E | CRITICAL | Cross-browser, auto-waiting, trace |
| https://www.cypress.io/how-it-works | E2E | HIGH | Time-travel, real browser |
| https://testing-library.com/docs/react-testing-library/intro | Unit | CRITICAL | User-centric, accessibility |
| https://mswjs.io/docs | Mocking | HIGH | API mocking, REST/GraphQL |
| https://webdriver.io/docs/gettingstarted | Automation | LOW | WebDriver automation |
| https://mochajs.org/#getting-started | Framework | LOW | Simple, flexible |
| https://github.com/avajs/ava | Framework | LOW | Concurrent, async |

### Python Testing
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://pytest.org/en/latest/ | Framework | HIGH | Powerful Python testing |
| https://docs.pytest.org/en/stable/reference/reference.html | Reference | HIGH | Pytest API reference |
| https://unittest.readthedocs.io/en/latest/ | Framework | MEDIUM | Python standard library |
| https://robotframework.org/#documentation | Framework | LOW | ATDD, keyword-driven |
| https://nose2.readthedocs.io/en/latest/ | Framework | LOW | Extension of unittest |

### Testing Tools
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://github.com/hapijs/lab | Tool | MEDIUM | Node.js assertion library |
| https://github.com/atinfo/awesome-test-automation | List | LOW | Test automation resources |
| https://github.com/kybarg/awesome-testing | List | LOW | Testing resources curated |

### Meta-Resources
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://introduct.tech/blog/top-javascript-testing-framework/ | List | HIGH | Top JS testing frameworks |
| https://www.browserstack.com/guide/top-python-testing-frameworks | List | HIGH | Top Python testing |
| https://github.com/jest-community/awesome-jest | List | MEDIUM | Jest ecosystem |
| https://github.com/TheBrainFamily/awesome-playwright | List | MEDIUM | Playwright resources |
| https://github.com/cypress-io/cypress-awesome-list | List | MEDIUM | Cypress ecosystem |

---

## 🐳 DEVOPS RESOURCES (20)

### Container & Orchestration
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://docs.docker.com/get-started | Containers | CRITICAL | Docker, Compose, build, deploy |
| https://kubernetes.io/docs/home/ | Orchestration | CRITICAL | K8s, Helm, Operators |
| https://helm.sh/docs/ | Package | HIGH | Helm charts, templates, releases |

### Monitoring & Observability
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://prometheus.io/docs/introduction/overview | Monitoring | HIGH | Time-series, alerting, service discovery |
| https://grafana.com/docs/ | Dashboards | HIGH | Metrics, logs, traces, alerts |

### IaC & Config
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://www.terraform.io/docs | IaC | HIGH | Infrastructure as Code, providers |
| https://www.ansible.com/resources/get-started | Automation | HIGH | Configuration management |

### CI/CD
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://www.jenkins.io/doc/ | CI | HIGH | Jenkins Pipeline, plugins |
| https://docs.gitlab.com/ee/ci/ | CI | HIGH | GitLab CI, caching, artifacts |
| https://docs.github.com/en/actions | CI | CRITICAL | GitHub Actions, workflows |
| https://circleci.com/docs/ | CI | MEDIUM | CircleCI, caching, matrix |

### Meta-Resources
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://www.pulumi.com/docs/ | IaC | HIGH | Pulumi - real programming languages |
| https://devopscube.com/best-devops-tools/ | List | HIGH | Curated DevOps tools list |
| http://awesome-devops.xyz | List | MEDIUM | Awesome DevOps list |
| https://github.com/wmariuss/awesome-devops | List | HIGH | Curated DevOps resources |
| https://github.com/awesome-selfhosted/awesome-selfhosted | List | HIGH | Self-hosted services |
| https://github.com/awesome-soft/awesome-devops | List | HIGH | DevOps software |
| https://github.com/techiescamp/devops-tools | List | LOW | DevOps tool comparisons |
| https://spacelift.io/blog/devops-tools | List | MEDIUM | DevOps tools review |
| https://www.atlassian.com/devops/devops-tools | List | HIGH | Atlassian's DevOps tool guide |

---

## 🛠️ BUILD TOOLS & BUNDLERS (10)

| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://vitejs.dev/guide/ | Bundler | CRITICAL | Fast dev server, HMR, optimized builds |
| https://webpack.js.org/concepts/ | Bundler | HIGH | Highly configurable, loaders, plugins |
| https://rollupjs.org/introduction/ | Bundler | HIGH | Tree-shaking, code-splitting |
| https://esbuild.github.io/getting-started/ | Bundler | HIGH | Fast, simple, Go-written |
| https://parceljs.org/getting-started/webapp/ | Bundler | MEDIUM | Zero-config, HMR |
| https://babeljs.io/docs/en/ | Transpiler | MEDIUM | JavaScript compiler, presets |
| https://swc.rs/docs/getting-started/ | Transpiler | HIGH | Fast JS/TS transpiler |
| https://turbo.build/repo/docs/ | Monorepo | HIGH | Turborepo, caching, remote execution |
| https://nx.dev/getting-started/intro | Monorepo | HIGH | Monorepo, caching, task orchestration |
| https://github.com/lerna/lerna#readme | Monorepo | MEDIUM | Lerna for JS/TS monorepos |

---

## 🔍 LINTING & FORMATTING (8)

| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://eslint.org/docs/latest/user-guide/getting-started | Linter | CRITICAL | Pluggable, rules, autofix |
| https://prettier.io/docs/en/index.html | Formatter | HIGH | Code formatter, opinionated |
| https://stylelint.io/user-guide/get-started | CSS Linter | MEDIUM | CSS linter, fixer |
| https://commitlint.js.org/#/guides/getting-started | Commit | MEDIUM | Commit linting |
| https://github.com/okonet/lint-staged | Tool | MEDIUM | Lint staged files |
| https://github.com/typicode/husky | Tool | HIGH | Git hooks made easy |
| https://github.com/conventional-changelog/commitlint/tree/master/@commitlint/config-conventional | Config | LOW | Conventional commits |
| https://semantic-release.gitbook.io/semantic-release/ | Release | MEDIUM | Automated release management |

### Code Style
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://github.com/airbnb/javascript | Style | HIGH | JavaScript style guide |
| https://github.com/standard/standard | Style | MEDIUM | JavaScript linter + formatter |

---

## 📧 EMAIL & NOTIFICATIONS (6)

| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://react-email.dev/docs | Email | MEDIUM | React components for email |
| https://resend.com/docs/send-with-react | Service | MEDIUM | Resend email service |
| https://nodemailer.com/about/ | Library | HIGH | Node.js email client |
| https://docs.sendgrid.com/for-developers/sending-email/api-getting-started | Service | MEDIUM | SendGrid email API |
| https://github.com/forwardemail/email-templates | Templates | LOW | Email template collection |
| https://github.com/kingcody/awesome-email | List | MEDIUM | Email resources |

---

## 🔌 APIS & SPECIFICATIONS (5)

| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://openapi-generator.tech/docs/overview | Generator | MEDIUM | Generate clients from OpenAPI |
| https://github.com/drwpow/openapi-typescript | Types | MEDIUM | TypeScript for OpenAPI |
| https://stoplight.io/open-source/prism/ | Mock | MEDIUM | Prism API mocking |
| https://hoppscotch.io/docs | Tool | LOW | HTTP toolkit |
| https://devopscube.com/best-devops-tools/ | List | HIGH | Best DevOps tools |

---

## 📚 LEARNING & ROADMAPS (12)

| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://github.com/lnishan/awesome-competitive-programming | Learning | LOW | Competitive programming |
| https://github.com/danistefanovic/build-your-own-x | Learning | HIGH | Re-implement tech from scratch |
| https://github.com/practical-tutorials/project-based-learning | Learning | HIGH | Project-based tutorials |
| https://github.com/getify/You-Dont-Know-JS | Book | HIGH | Deep JS knowledge |
| https://github.com/kamranahmedse/developer-roadmap | Roadmap | CRITICAL | Developer roadmap |
| https://github.com/codecrafters-io/build-your-own-x | Learning | HIGH | Build your own tech |
| https://roadmap.sh/ | Roadmap | HIGH | Developer roadmaps |
| https://refactoring.guru/design-patterns | Patterns | HIGH | Design patterns catalog |
| https://martinfowler.com/articles/microservices.html | Architecture | HIGH | Microservices article |
| https://12factor.net/ | Architecture | HIGH | Twelve-Factor App methodology |

### Specialized
| Resource | Type | Priority | Notes |
|----------|------|----------|-------|
| https://agents.md | AI | HIGH | AI agents documentation |
| https://browseract.com | Browser | LOW | Browser automation |

---

## 🎯 DEFAULT STACK TEMPLATE

When starting a new project, use this modern stack:

```
Frontend: Next.js 15+ App Router
  - https://nextjs.org/docs
  - https://react.dev/learn
  
State: TanStack (Query + Router)
  - https://tanstack.com/query/latest/docs/framework/react/overview
  - https://tanstack.com/router/latest/docs/framework/react/overview
  
API: tRPC
  - https://tRPC.io/docs
  
Database: Prisma + PostgreSQL
  - https://www.prisma.io/docs
  - https://www.postgresql.org/docs
  
Validation: Zod
  - https://zod.dev/
  
Styling: Tailwind CSS + Shadcn UI
  - https://tailwindcss.com/docs
  - https://ui.shadcn.com/docs
  
Testing: Vitest + Playwright
  - https://vitest.dev/guide
  - https://playwright.dev/docs/intro
  
DevOps: Docker + GitHub Actions
  - https://docs.docker.com/get-started
  - https://docs.github.com/en/actions
```

---

## 🔄 EXECUTION RULES

### When Starting Any Task
"Knowledge updated from 120+ resources. Using [specific links] for this solution."

### Code Generation
- Reference exact docs patterns, not generic knowledge
- Always cite 3-5 specific resources used
- Use TypeScript-first approach
- Include testing, linting, formatting

### Stack Recommendations
- Justify with specific links from this list
- Prioritize resources marked CRITICAL/HIGH
- Default to modern stack when appropriate

### Self-Improvement
- Cross-reference new tech against this list first
- Update internal patterns weekly
- Scan for documentation updates

### Weekly Audit
- Scan list for updates
- Regenerate internal patterns
- Add new modern resources

---

## 📊 RESOURCE STATISTICS

- **Total Resources**: 120+
- **CRITICAL Priority**: 15 (12.5%)
- **HIGH Priority**: 55 (45.8%)
- **MEDIUM Priority**: 40 (33.3%)
- **LOW Priority**: 10 (8.3%)
- **Frontend**: 30 (25%)
- **Backend**: 25 (20.8%)
- **Database**: 20 (16.7%)
- **Testing**: 15 (12.5%)
- **DevOps**: 20 (16.7%)
- **Build Tools**: 10 (8.3%)
- **Linting**: 8 (6.7%)
- **Email**: 6 (5%)
- **APIs**: 5 (4.2%)
- **Learning**: 12 (10%)

---

**Knowledge Base Last Updated**: February 2, 2026  
**Next Audit Scheduled**: February 9, 2026