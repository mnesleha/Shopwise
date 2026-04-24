export default function ShopwiseShowcaseHomepage() {
  const sections = [
    {
      title: "What this project is",
      body: "Shopwise is a solo-built showcase project created to demonstrate a quality-driven approach to software delivery. It combines a realistic customer-facing storefront, admin and business workflows, provider-based payment architecture, email-driven flows, reproducible seeded demo scenarios, and a test/documentation strategy designed to support maintainability and trust.",
    },
    {
      title: "What this demo shows",
      body: "The public demo is intentionally seeded and structured to make key business flows easy to understand and reproduce. It highlights guest checkout, authenticated customer journeys, promotions and campaign logic, and the operational/admin perspective behind the storefront.",
    },
    {
      title: "Why quality-driven",
      body: "This project was built to make quality visible in both implementation and presentation. That includes architecture decisions captured through ADRs, API-first documentation, multiple layers of automated tests, reproducible seed-driven demo scenarios, and deployment of the full stack instead of a static mockup.",
    },
    {
      title: "Architecture and direction",
      body: "Shopwise is intentionally structured around provider-based integration boundaries and deployable service separation. The current showcase includes a Next.js frontend, a Django + DRF backend, async/background processing, a mock payment provider, email preview infrastructure, hosted MySQL, and object storage for media.",
    },
  ];

  const cards = [
    {
      title: "End-to-end commerce flows",
      text: "Catalog, cart, checkout, payment, email, and order scenarios in a deployed public demo.",
    },
    {
      title: "Quality-first engineering",
      text: "Architecture decisions, test layers, OpenAPI, documentation, and reproducible seeded scenarios.",
    },
    {
      title: "Product-oriented architecture",
      text: "Provider-based design and deployment structure prepared for future starterkit or white-label evolution.",
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <div className="text-lg font-semibold tracking-tight">Shopwise</div>
            <div className="text-sm text-slate-500">
              Quality-Driven E-commerce Showcase
            </div>
          </div>
          <nav className="flex items-center gap-6 text-sm text-slate-600">
            <a href="#about" className="hover:text-slate-900">
              About
            </a>
            <a href="#quality" className="hover:text-slate-900">
              Quality
            </a>
            <a href="#architecture" className="hover:text-slate-900">
              Architecture
            </a>
            <a
              href="/products"
              className="rounded-2xl bg-slate-900 px-4 py-2 font-medium text-white shadow-sm hover:bg-slate-800"
            >
              Enter Demo
            </a>
          </nav>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl gap-12 px-6 py-20 md:grid-cols-[1.2fr_0.8fr] md:items-center">
          <div>
            <div className="mb-4 inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
              CV Showcase / Portfolio Project
            </div>
            <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl">
              Shopwise — Quality-Driven E-commerce Showcase
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              A full-stack showcase project focused on end-to-end product
              thinking, business workflows, and quality engineering.
            </p>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-500">
              This project demonstrates how a modern commerce application can be
              designed, tested, documented, and deployed with quality as a
              first-class concern — not as an afterthought.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <a
                href="/products"
                className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-medium text-white shadow-sm hover:bg-slate-800"
              >
                Enter Demo
              </a>
              <a
                href="#about"
                className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-medium text-slate-700 hover:bg-slate-100"
              >
                Explore the Project
              </a>
              <a
                href="https://mnesleha.github.io/Shopwise/demo/readme/"
                className="rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-medium text-slate-700 hover:bg-slate-100"
              >
                See demo scenarios
              </a>
            </div>
          </div>

          <div className="grid gap-4">
            {cards.map((card) => (
              <div
                key={card.title}
                className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <h3 className="text-lg font-semibold tracking-tight">
                  {card.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">
                  {card.text}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section id="about" className="mx-auto max-w-5xl px-6 py-6">
          <div className="rounded-4xl border border-slate-200 bg-white p-8 shadow-sm md:p-10">
            <div className="grid gap-10">
              {sections.map((section, index) => (
                <div
                  key={section.title}
                  id={
                    index === 2
                      ? "quality"
                      : index === 3
                        ? "architecture"
                        : undefined
                  }
                >
                  <h2 className="text-2xl font-semibold tracking-tight text-slate-950">
                    {section.title}
                  </h2>
                  <p className="mt-4 max-w-3xl text-base leading-8 text-slate-600">
                    {section.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-6 py-12">
          <div className="grid gap-6 rounded-4xl border border-slate-200 bg-slate-900 p-8 text-slate-50 shadow-sm md:grid-cols-[1fr_auto] md:items-center md:p-10">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">
                Explore further
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
                Use the demo storefront to explore the customer-facing flows,
                then continue to the project documentation, API docs, and
                architecture notes for technical detail.
              </p>
              <div className="mt-5 flex flex-wrap gap-3 text-sm text-slate-300">
                <a
                  href="https://github.com/mnesleha/Shopwise"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-full border border-slate-700 px-3 py-1 hover:bg-slate-700 hover:text-white transition-colors"
                >
                  GitHub Repository
                </a>
                <a
                  href="https://mnesleha.github.io/Shopwise/demo/readme/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-full border border-slate-700 px-3 py-1 hover:bg-slate-700 hover:text-white transition-colors"
                >
                  Demo scenarios
                </a>
                <a
                  href="https://shopwise-backend-ljqn.onrender.com/api/docs/swagger/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-full border border-slate-700 px-3 py-1 hover:bg-slate-700 hover:text-white transition-colors"
                >
                  API Docs
                </a>
                <a
                  href="https://github.com/mnesleha/Shopwise/blob/main/docs/decisions/readme.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-full border border-slate-700 px-3 py-1 hover:bg-slate-700 hover:text-white transition-colors"
                >
                  ADR
                </a>
                <a
                  href="https://github.com/mnesleha/Shopwise/blob/main/docs/testing/readme.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-full border border-slate-700 px-3 py-1 hover:bg-slate-700 hover:text-white transition-colors"
                >
                  Testing Strategy
                </a>
              </div>
            </div>
            <a
              href="/products"
              className="inline-flex h-fit rounded-2xl bg-white px-5 py-3 text-sm font-medium text-slate-900 hover:bg-slate-100"
            >
              Open Storefront
            </a>
          </div>
        </section>
      </main>
    </div>
  );
}
