import Link from "next/link";

const STEPS = [
  {
    step: "01",
    title: "Create your profile",
    description: "Add your dietary needs, allergies, and location.",
  },
  {
    step: "02",
    title: "Ask the assistant",
    description: "Request restaurant options and meal guidance nearby.",
  },
  {
    step: "03",
    title: "Choose confidently",
    description: "Review recommendations and pick what works for you.",
  },
];

const QUICK_POINTS = [
  "Personalized recommendations",
  "Allergy-aware guidance",
  "Simple, fast setup",
];

export default function LandingPage() {
  return (
    <main className="landing-main">
      <section className="hero hero--simple">
        <div className="hero-inner">
          <p className="eyebrow">Nourish.ai</p>
          <h1 className="hero-heading">
            Find restaurants that fit
            <span className="hero-accent"> your dietary profile</span>
          </h1>
          <p className="hero-sub">
            Get straightforward recommendations based on your health needs and allergies.
          </p>

          <div className="hero-actions">
            <Link href="/profile" className="btn-primary">
              Create profile
            </Link>
            <Link href="/chat" className="btn-ghost">
              Open assistant
            </Link>
          </div>

          <ul className="hero-list" aria-label="Key benefits">
            {QUICK_POINTS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="steps-section steps-section--simple">
        <div className="section-shell">
          <p className="section-eyebrow">How it works</p>
          <h2 className="section-heading">Three simple steps</h2>

          <div className="steps-grid steps-grid--simple">
            {STEPS.map((step) => (
              <article className="step-card" key={step.step}>
                <span className="step-number">{step.step}</span>
                <h3 className="step-title">{step.title}</h3>
                <p className="step-desc">{step.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
